from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable
from pathlib import Path

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import async_playwright

from .time_utils import live_slug, seconds_remaining_from_slug, slug_to_url, utc_now
from .types import PageMarketData

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PageHandler = Callable[[PageMarketData], Awaitable[None]]


def money_to_float(value: str) -> float:
    return float(value.replace("$", "").replace(",", "").strip())


def extract_big_money_after_label(text: str, label: str) -> float | None:
    label_match = re.search(re.escape(label), text, re.IGNORECASE)
    if not label_match:
        return None

    start = label_match.end()
    window = text[start : start + 300]
    money_matches = re.findall(r"\$?\s*([\d,]+(?:\.\d+)?)", window)

    for value in money_matches:
        try:
            number = money_to_float(value)
            if number > 1000:
                return number
        except ValueError:
            continue
    return None


def extract_seconds_remaining(text: str) -> int | None:
    """Read the visible countdown when available.

    Polymarket can render this differently depending on language/layout. The
    slug-based fallback in parse_polymarket_text is the source of stability.
    """
    patterns = [
        r"(\d{1,2})\s*MIN\s*(\d{1,2})\s*SEGS",
        r"(\d{1,2})\s*min\s*(\d{1,2})\s*seg",
        r"(\d{1,2})\s*:\s*(\d{2})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1)) * 60 + int(match.group(2))
    return None


def parse_polymarket_text(text: str, slug: str) -> PageMarketData:
    current_price = (
        extract_big_money_after_label(text, "Precio actual")
        or extract_big_money_after_label(text, "Current price")
    )
    strike_price = (
        extract_big_money_after_label(text, "Precio a superar")
        or extract_big_money_after_label(text, "Price to beat")
    )

    # 1) Try the visible countdown.
    # 2) If Polymarket changes the text/layout, compute time from the slug.
    seconds_remaining = extract_seconds_remaining(text)
    if seconds_remaining is None:
        seconds_remaining = seconds_remaining_from_slug(slug)

    return PageMarketData(
        slug=slug,
        current_price=current_price,
        strike_price=strike_price,
        seconds_remaining=seconds_remaining,
        scraped_at=utc_now(),
    )


async def _launch_browser(playwright, edge_path: str | None, headless: bool):
    launch_kwargs = {"headless": headless}
    if edge_path and Path(edge_path).exists():
        try:
            return await playwright.chromium.launch(executable_path=edge_path, **launch_kwargs)
        except PlaywrightError as exc:
            print(f"[page] No pude lanzar Edge configurado: {exc}. Intentando Chromium por defecto.")
    return await playwright.chromium.launch(**launch_kwargs)


async def stream_polymarket_page(
    on_page: PageHandler,
    interval_seconds: float = 1.0,
    market_url: str | None = None,
    edge_path: str | None = EDGE_PATH,
    headless: bool = True,
) -> None:
    """Scrape visible Polymarket page fields used as round metadata.

    This is intentionally not the source of truth for execution. It is used to
    obtain the visible strike and countdown when no cleaner API source is wired.
    """
    explicit_market_url = market_url

    while True:
        slug = live_slug() if explicit_market_url is None else explicit_market_url.rstrip("/").split("/")[-1]
        active_market_url = explicit_market_url or slug_to_url(slug)

        try:
            async with async_playwright() as p:
                browser = await _launch_browser(p, edge_path=edge_path, headless=headless)
                page = await browser.new_page(viewport={"width": 1400, "height": 900})

                try:
                    await page.goto(active_market_url, wait_until="domcontentloaded", timeout=30_000)
                    try:
                        await page.wait_for_function(
                            "() => document.body && (document.body.innerText.includes('Precio actual') || document.body.innerText.includes('Current price'))",
                            timeout=20_000,
                        )
                    except PlaywrightTimeoutError:
                        print("[page] No apareció el bloque principal del mercado. Reintentando en 1s...")
                        await asyncio.sleep(1.0)
                        continue

                    while True:
                        latest_slug = live_slug() if explicit_market_url is None else slug
                        if latest_slug != slug:
                            break
                        text = await page.locator("body").inner_text(timeout=5_000)
                        await on_page(parse_polymarket_text(text, slug))
                        await asyncio.sleep(interval_seconds)
                finally:
                    await browser.close()
        except (PlaywrightError, OSError) as exc:
            print(f"[page] Error del navegador/scraper: {exc}. Reintentando en 1s...")
            await asyncio.sleep(1.0)
