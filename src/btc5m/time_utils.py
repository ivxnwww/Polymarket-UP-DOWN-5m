from __future__ import annotations

import time
from datetime import datetime, timezone

ROUND_SECONDS = 300


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_exchange_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def current_round_timestamp(now_unix: int | None = None, interval: int = ROUND_SECONDS) -> int:
    now_unix = now_unix if now_unix is not None else int(time.time())
    return (now_unix // interval) * interval


def timestamp_to_slug(ts: int) -> str:
    return f"btc-updown-5m-{ts}"


def live_slug(interval: int = ROUND_SECONDS) -> str:
    return timestamp_to_slug(current_round_timestamp(interval=interval))


def slug_to_url(slug: str, lang: str = "es") -> str:
    return f"https://polymarket.com/{lang}/event/{slug}"


def slug_to_round_start(slug: str) -> int | None:
    """Extract the unix start timestamp from a Polymarket BTC 5m slug.

    Example:
        btc-updown-5m-1781297700 -> 1781297700
    """
    try:
        return int(slug.rstrip('/').split('-')[-1])
    except (TypeError, ValueError):
        return None


def seconds_remaining_from_slug(
    slug: str,
    now_unix: int | None = None,
    interval: int = ROUND_SECONDS,
) -> int | None:
    """Compute remaining seconds from the market slug instead of page text.

    This is more stable than scraping the visible countdown because the slug
    contains the round start timestamp and each BTC Up/Down round lasts 300s.
    """
    round_start = slug_to_round_start(slug)
    if round_start is None:
        return None

    now_unix = now_unix if now_unix is not None else int(time.time())
    round_end = round_start + interval
    remaining = round_end - now_unix

    # Clamp to the normal range so a stale/next slug does not create nonsense.
    return max(0, min(interval, int(remaining)))
