from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .time_utils import seconds_remaining_from_slug
from .types import BtcTick, OutcomeBook, PageMarketData


@dataclass(slots=True)
class MarketSnapshot:
    btc_tick: BtcTick | None
    page: PageMarketData | None
    books: dict[str, OutcomeBook]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def strike_price(self) -> float | None:
        return self.page.strike_price if self.page else None

    @property
    def seconds_remaining(self) -> int | None:
        if not self.page:
            return None
        if self.page.seconds_remaining is not None:
            return self.page.seconds_remaining
        return seconds_remaining_from_slug(self.page.slug)

    @property
    def page_current_price(self) -> float | None:
        return self.page.current_price if self.page else None

    def book(self, side: str) -> OutcomeBook | None:
        return self.books.get(side.upper())


class SharedMarketState:
    """Async-safe latest-value store for feeds.

    The feeds write raw normalized data here. Models read a snapshot every
    dashboard cycle. This keeps the dashboard and bot from depending on print()
    output or Playwright text directly.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._btc_tick: BtcTick | None = None
        self._page: PageMarketData | None = None
        self._books: dict[str, OutcomeBook] = {}

    async def update_btc(self, tick: BtcTick) -> None:
        async with self._lock:
            self._btc_tick = tick

    async def update_page(self, page: PageMarketData) -> None:
        async with self._lock:
            self._page = page

    async def update_book(self, book: OutcomeBook) -> None:
        async with self._lock:
            self._books[str(book.normalized_outcome).upper()] = book

    async def snapshot(self) -> MarketSnapshot:
        async with self._lock:
            return MarketSnapshot(
                btc_tick=self._btc_tick,
                page=self._page,
                books=dict(self._books),
            )
