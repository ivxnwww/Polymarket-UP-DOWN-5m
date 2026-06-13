from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from .state import MarketSnapshot
from .types import SignalOutput


FEATURE_COLUMNS = [
    "round_slug",
    "timestamp",
    "seconds_remaining",
    "clean_price",
    "strike_price",
    "distance_to_strike",
    "z_score",
    "sigma_per_sqrt_second",
    "p_up_base",
    "p_up_final",
    "reversal_probability",
    "up_bid",
    "up_ask",
    "down_bid",
    "down_ask",
    "spread_up",
    "spread_down",
    "edge_buy_up",
    "edge_buy_down",
    "data_age_ms",
    "exchange_latency_ms",
    # Label filled after settlement:
    "result_up",
]


def build_feature_row(snapshot: MarketSnapshot, signal: SignalOutput, result_up: int | None = None) -> dict:
    up_book = snapshot.book("UP")
    down_book = snapshot.book("DOWN")
    distance = None
    if signal.clean_price is not None and signal.strike_price is not None:
        distance = signal.clean_price - signal.strike_price

    return {
        "round_slug": snapshot.page.slug if snapshot.page else None,
        "timestamp": signal.timestamp.isoformat(),
        "seconds_remaining": signal.seconds_remaining,
        "clean_price": signal.clean_price,
        "strike_price": signal.strike_price,
        "distance_to_strike": distance,
        "z_score": signal.z_score,
        "sigma_per_sqrt_second": signal.sigma_per_sqrt_second,
        "p_up_base": signal.p_up_base,
        "p_up_final": signal.p_up_final,
        "reversal_probability": signal.reversal_probability,
        "up_bid": signal.up_bid,
        "up_ask": signal.up_ask,
        "down_bid": signal.down_bid,
        "down_ask": signal.down_ask,
        "spread_up": up_book.spread if up_book else None,
        "spread_down": down_book.spread if down_book else None,
        "edge_buy_up": signal.edge_buy_up,
        "edge_buy_down": signal.edge_buy_down,
        "data_age_ms": signal.data_age_ms,
        "exchange_latency_ms": signal.exchange_latency_ms,
        "result_up": result_up,
    }


class CsvFeatureWriter:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._header_written = self.path.exists() and self.path.stat().st_size > 0

    def append(self, row: dict) -> None:
        with self.path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FEATURE_COLUMNS)
            if not self._header_written:
                writer.writeheader()
                self._header_written = True
            writer.writerow({key: row.get(key) for key in FEATURE_COLUMNS})
