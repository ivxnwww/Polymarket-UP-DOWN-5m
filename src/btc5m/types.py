from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

Side = Literal["UP", "DOWN"]
Action = Literal["WAIT", "BUY_UP", "BUY_DOWN", "HOLD", "SELL", "SELL_PARTIAL"]


@dataclass(slots=True)
class BtcTick:
    price: float
    exchange_time: datetime
    received_at: datetime
    product_id: str = "BTC-USD"

    @property
    def latency_ms(self) -> float:
        return max(0.0, (self.received_at - self.exchange_time).total_seconds() * 1000.0)

    def age_ms(self, now: datetime | None = None) -> float:
        now = now or datetime.now(timezone.utc)
        return max(0.0, (now - self.received_at).total_seconds() * 1000.0)


@dataclass(slots=True)
class BookLevel:
    price: float
    size: float


@dataclass(slots=True)
class OutcomeBook:
    outcome: str
    token_id: str
    bids: list[BookLevel] = field(default_factory=list)
    asks: list[BookLevel] = field(default_factory=list)
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def normalized_outcome(self) -> Side | str:
        value = self.outcome.upper()
        if value in {"UP", "YES", "ARRIBA", "HIGHER"}:
            return "UP"
        if value in {"DOWN", "NO", "ABAJO", "LOWER"}:
            return "DOWN"
        return value

    @property
    def best_bid(self) -> float | None:
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> float | None:
        return self.asks[0].price if self.asks else None

    @property
    def spread(self) -> float | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return max(0.0, self.best_ask - self.best_bid)

    @property
    def mid(self) -> float | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return (self.best_bid + self.best_ask) / 2.0

    def bid_depth(self, levels: int = 5) -> float:
        return sum(level.size for level in self.bids[:levels])

    def ask_depth(self, levels: int = 5) -> float:
        return sum(level.size for level in self.asks[:levels])

    def imbalance(self, levels: int = 5) -> float:
        bid = self.bid_depth(levels)
        ask = self.ask_depth(levels)
        total = bid + ask
        if total <= 0:
            return 0.0
        return (bid - ask) / total


@dataclass(slots=True)
class PageMarketData:
    slug: str
    current_price: float | None
    strike_price: float | None
    seconds_remaining: int | None
    scraped_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def difference(self) -> float | None:
        if self.current_price is None or self.strike_price is None:
            return None
        return self.current_price - self.strike_price


@dataclass(slots=True)
class Position:
    side: Side
    entry_price: float
    quantity: float
    entry_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class SignalOutput:
    timestamp: datetime
    action: Action
    reason: str
    clean_price: float | None
    strike_price: float | None
    seconds_remaining: int | None
    sigma_per_sqrt_second: float | None
    z_score: float | None
    p_up_base: float | None
    p_up_final: float | None
    p_down_final: float | None
    reversal_probability: float | None
    up_bid: float | None
    up_ask: float | None
    down_bid: float | None
    down_ask: float | None
    edge_buy_up: float | None
    edge_buy_down: float | None
    edge_hold: float | None = None
    sell_value: float | None = None
    data_age_ms: float | None = None
    exchange_latency_ms: float | None = None
