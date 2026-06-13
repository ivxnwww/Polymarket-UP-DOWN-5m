from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from urllib.parse import urlparse

import requests
import websockets
from requests import RequestException

from .time_utils import live_slug, slug_to_url, utc_now
from .types import BookLevel, OutcomeBook

WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
CLOB_BOOK_URL = "https://clob.polymarket.com/book"
GAMMA_EVENT_BY_SLUG = "https://gamma-api.polymarket.com/events/slug/{slug}"
BookHandler = Callable[[OutcomeBook], Awaitable[None]]
HTTP_SESSION = requests.Session()
HTTP_SESSION.trust_env = False


def extract_slug(url: str) -> str:
    return urlparse(url).path.strip("/").split("/")[-1]


def parse_json_field(value):
    if isinstance(value, str):
        return json.loads(value)
    return value


def normalize_outcome_name(name: str) -> str:
    value = name.strip().upper()
    if value in {"UP", "YES", "ARRIBA", "HIGHER"}:
        return "UP"
    if value in {"DOWN", "NO", "ABAJO", "LOWER"}:
        return "DOWN"
    return value


def _get_json(url: str, **kwargs) -> dict:
    response = HTTP_SESSION.get(url, **kwargs)
    response.raise_for_status()
    return response.json()


def get_token_ids_from_slug(slug: str) -> dict[str, str]:
    event_url = GAMMA_EVENT_BY_SLUG.format(slug=slug)
    event = _get_json(event_url, timeout=15)
    market = event["markets"][0]
    outcomes = parse_json_field(market["outcomes"])
    token_ids = parse_json_field(market["clobTokenIds"])

    return {normalize_outcome_name(outcome): str(token_id) for outcome, token_id in zip(outcomes, token_ids)}


def get_orderbook_rest(token_id: str) -> dict:
    return _get_json(CLOB_BOOK_URL, params={"token_id": token_id}, timeout=10)


def _parse_levels(levels: list[dict], reverse: bool) -> list[BookLevel]:
    parsed: list[BookLevel] = []
    for level in levels:
        try:
            parsed.append(BookLevel(price=float(level.get("price", 0)), size=float(level.get("size", 0))))
        except (TypeError, ValueError):
            continue
    return sorted(parsed, key=lambda x: x.price, reverse=reverse)


def outcome_from_token(token_id: str, token_map: dict[str, str]) -> str:
    for outcome, known_token in token_map.items():
        if str(known_token) == str(token_id):
            return outcome
    return "UNKNOWN"


def book_from_raw(outcome: str, token_id: str, bids: list[dict], asks: list[dict]) -> OutcomeBook:
    return OutcomeBook(
        outcome=normalize_outcome_name(outcome),
        token_id=str(token_id),
        bids=_parse_levels(bids, reverse=True),
        asks=_parse_levels(asks, reverse=False),
        updated_at=utc_now(),
    )


def msg_belongs_to_target_market(msg: dict, target_asset_ids: set[str]) -> bool:
    asset_id = msg.get("asset_id")
    if asset_id and str(asset_id) in target_asset_ids:
        return True
    for pc in msg.get("price_changes", []):
        pc_asset_id = pc.get("asset_id")
        if pc_asset_id and str(pc_asset_id) in target_asset_ids:
            return True
    return False


async def emit_initial_rest_books(on_book: BookHandler, token_map: dict[str, str]) -> None:
    for outcome, token_id in token_map.items():
        try:
            book = get_orderbook_rest(token_id)
            await on_book(book_from_raw(outcome, token_id, book.get("bids", []), book.get("asks", [])))
        except Exception as exc:
            print(f"[polymarket] No pude consultar book inicial {outcome}: {exc}")


async def stream_polymarket_books(
    on_book: BookHandler,
    market_url: str | None = None,
    slug: str | None = None,
) -> None:
    """Stream Polymarket CLOB book data for the current or specified 5m market."""
    explicit_slug = slug
    explicit_market_url = market_url
    while True:
        try:
            active_slug = explicit_slug or (extract_slug(explicit_market_url) if explicit_market_url else live_slug())
            active_market_url = explicit_market_url or slug_to_url(active_slug)
            token_map = get_token_ids_from_slug(active_slug)
            target_asset_ids = set(str(asset_id) for asset_id in token_map.values())
            await emit_initial_rest_books(on_book, token_map)

            async with websockets.connect(WS_URL, ping_interval=None, close_timeout=5) as ws:
                subscription = {
                    "type": "market",
                    "assets_ids": list(token_map.values()),
                    "custom_feature_enabled": False,
                }
                await ws.send(json.dumps(subscription))
                print(f"[polymarket] Conectado a {active_market_url}")

                async def heartbeat() -> None:
                    while True:
                        await asyncio.sleep(10)
                        if explicit_slug is None and explicit_market_url is None and live_slug() != active_slug:
                            await ws.close()
                            return
                        await ws.send("PING")

                hb_task = asyncio.create_task(heartbeat())

                try:
                    async for raw in ws:
                        if raw in ("PONG", ""):
                            continue
                        try:
                            data = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        if data == {}:
                            continue

                        messages = [data] if isinstance(data, dict) else data if isinstance(data, list) else []
                        for msg in messages:
                            if not isinstance(msg, dict) or not msg_belongs_to_target_market(msg, target_asset_ids):
                                continue

                            event_type = msg.get("event_type")

                            if event_type == "book":
                                asset_id = str(msg.get("asset_id"))
                                outcome = outcome_from_token(asset_id, token_map)
                                await on_book(book_from_raw(outcome, asset_id, msg.get("bids", []), msg.get("asks", [])))

                            elif event_type == "price_change":
                                # price_change messages carry best_bid/best_ask, but not a full book.
                                # We emit a lightweight top-of-book object so the engine can update quotes.
                                for pc in msg.get("price_changes", []):
                                    asset_id = str(pc.get("asset_id"))
                                    if asset_id not in target_asset_ids:
                                        continue
                                    outcome = outcome_from_token(asset_id, token_map)
                                    bids = []
                                    asks = []
                                    if pc.get("best_bid") is not None:
                                        bids.append({"price": pc.get("best_bid"), "size": pc.get("size", 0)})
                                    if pc.get("best_ask") is not None:
                                        asks.append({"price": pc.get("best_ask"), "size": pc.get("size", 0)})
                                    await on_book(book_from_raw(outcome, asset_id, bids, asks))
                finally:
                    hb_task.cancel()
        except (websockets.ConnectionClosed, OSError, asyncio.TimeoutError, RequestException, KeyError, IndexError, ValueError) as exc:
            print(f"[polymarket] Conexion perdida: {exc}. Reintentando en 1s...")
            await asyncio.sleep(1.0)
