from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone

from .models import (
    EWMAVolatility,
    KalmanPriceVelocity,
    clamp,
    expected_value_buy,
    expected_value_hold,
    first_passage_probability_cross_strike,
    kelly_fraction_binary,
    safe_logit,
    sigmoid,
    terminal_probability_up,
    z_score_to_strike,
)
from .state import MarketSnapshot
from .types import OutcomeBook, Position, SignalOutput


@dataclass(slots=True)
class SignalConfig:
    ewma_lambda: float = 0.94
    min_edge_entry: float = 0.03
    min_hold_edge: float = 0.03
    min_seconds_to_trade: int = 5
    max_latency_ms: float = 750.0
    max_data_age_ms: float = 1500.0
    max_reversal_probability: float = 0.35
    use_kalman_price: bool = True

    # Manual small adjustments before ML. Keep them conservative.
    momentum_logit_weight: float = 0.35
    orderbook_logit_weight: float = 0.20
    max_logit_adjustment: float = 0.75


class SignalEngine:
    """Turns normalized market state into probability, edge and exit metrics."""

    def __init__(self, config: SignalConfig | None = None) -> None:
        self.config = config or SignalConfig()
        self.ewma = EWMAVolatility(lam=self.config.ewma_lambda)
        self.kalman = KalmanPriceVelocity()
        self._last_tick_key: tuple[datetime, float] | None = None

    def _update_price_models(self, snapshot: MarketSnapshot) -> tuple[float | None, float | None, float | None]:
        tick = snapshot.btc_tick
        if tick is None:
            return None, None, None

        tick_key = (tick.exchange_time, tick.price)
        if tick_key != self._last_tick_key:
            self.ewma.update(tick.price, tick.exchange_time)
            clean_price, velocity = self.kalman.update(tick.price, tick.exchange_time)
            self._last_tick_key = tick_key
        else:
            clean_price = self.kalman.price if self.kalman.price is not None else tick.price
            velocity = self.kalman.velocity

        if not self.config.use_kalman_price:
            clean_price = tick.price

        return clean_price, velocity, self.ewma.sigma

    @staticmethod
    def _quotes(book: OutcomeBook | None) -> tuple[float | None, float | None, float | None]:
        if book is None:
            return None, None, None
        return book.best_bid, book.best_ask, book.spread

    @staticmethod
    def _book_imbalance(up_book: OutcomeBook | None, down_book: OutcomeBook | None) -> float:
        if up_book is None or down_book is None:
            return 0.0
        # Positive means the UP book is stronger relative to DOWN.
        return clamp((up_book.imbalance() - down_book.imbalance()) / 2.0, -1.0, 1.0)

    def _adjust_probability(
        self,
        p_base: float,
        clean_price: float,
        velocity_usd_per_second: float | None,
        seconds_remaining: int,
        sigma_per_sqrt_second: float,
        up_book: OutcomeBook | None,
        down_book: OutcomeBook | None,
        latency_ms: float,
        data_age_ms: float,
    ) -> float:
        logit = safe_logit(p_base)

        momentum_adjustment = 0.0
        if velocity_usd_per_second is not None and clean_price > 0 and sigma_per_sqrt_second > 0 and seconds_remaining > 0:
            # Convert short-term velocity into expected log move over a capped horizon,
            # then scale it by expected noise. This keeps momentum comparable to z-score.
            horizon = min(float(seconds_remaining), 15.0)
            expected_log_move = (velocity_usd_per_second / clean_price) * horizon
            expected_noise = sigma_per_sqrt_second * math.sqrt(max(horizon, 1.0))
            if expected_noise > 0:
                momentum_z = clamp(expected_log_move / expected_noise, -2.0, 2.0)
                momentum_adjustment = self.config.momentum_logit_weight * momentum_z

        obi = self._book_imbalance(up_book, down_book)
        orderbook_adjustment = self.config.orderbook_logit_weight * obi

        total_adjustment = clamp(
            momentum_adjustment + orderbook_adjustment,
            -self.config.max_logit_adjustment,
            self.config.max_logit_adjustment,
        )
        p = sigmoid(logit + total_adjustment)

        # Latency and stale data do not tell direction. They reduce confidence by
        # pulling the probability toward 0.5.
        stale_ratio = max(latency_ms / self.config.max_latency_ms, data_age_ms / self.config.max_data_age_ms)
        if stale_ratio > 1.0:
            confidence = clamp(1.0 / stale_ratio, 0.25, 1.0)
            p = 0.5 + confidence * (p - 0.5)

        return clamp(p)

    def evaluate(self, snapshot: MarketSnapshot, position: Position | None = None) -> SignalOutput:
        now = datetime.now(timezone.utc)
        clean_price, velocity, sigma = self._update_price_models(snapshot)
        strike = snapshot.strike_price
        seconds_remaining = snapshot.seconds_remaining
        up_book = snapshot.book("UP")
        down_book = snapshot.book("DOWN")
        up_bid, up_ask, _ = self._quotes(up_book)
        down_bid, down_ask, _ = self._quotes(down_book)

        tick = snapshot.btc_tick
        data_age_ms = tick.age_ms(now) if tick else None
        latency_ms = tick.latency_ms if tick else None

        if clean_price is None or strike is None or seconds_remaining is None or sigma is None:
            return SignalOutput(
                timestamp=now,
                action="WAIT",
                reason="Faltan datos: BTC, strike/tiempo de Polymarket o volatilidad EWMA.",
                clean_price=clean_price,
                strike_price=strike,
                seconds_remaining=seconds_remaining,
                sigma_per_sqrt_second=sigma,
                z_score=None,
                p_up_base=None,
                p_up_final=None,
                p_down_final=None,
                reversal_probability=None,
                up_bid=up_bid,
                up_ask=up_ask,
                down_bid=down_bid,
                down_ask=down_ask,
                edge_buy_up=None,
                edge_buy_down=None,
                data_age_ms=data_age_ms,
                exchange_latency_ms=latency_ms,
            )

        p_base = terminal_probability_up(clean_price, strike, seconds_remaining, sigma)
        z = z_score_to_strike(clean_price, strike, seconds_remaining, sigma)
        p_up = self._adjust_probability(
            p_base=p_base,
            clean_price=clean_price,
            velocity_usd_per_second=velocity,
            seconds_remaining=seconds_remaining,
            sigma_per_sqrt_second=sigma,
            up_book=up_book,
            down_book=down_book,
            latency_ms=latency_ms or 0.0,
            data_age_ms=data_age_ms or 0.0,
        )
        p_down = 1.0 - p_up
        reversal_probability = first_passage_probability_cross_strike(clean_price, strike, seconds_remaining, sigma)

        edge_up = expected_value_buy(p_up, up_ask) if up_ask is not None else None
        edge_down = expected_value_buy(p_down, down_ask) if down_ask is not None else None

        action = "WAIT"
        reason = "Sin edge suficiente o faltan quotes operables."
        edge_hold = None
        sell_value = None

        if seconds_remaining <= self.config.min_seconds_to_trade:
            action = "WAIT"
            reason = "Muy cerca del cierre; evitar entrar por latencia y riesgo de mala ejecución."
        elif position is not None:
            if position.side == "UP":
                prob_win = p_up
                bid = up_bid
            else:
                prob_win = p_down
                bid = down_bid

            if bid is not None:
                edge_hold = expected_value_hold(prob_win, bid)
                sell_value = bid
                if edge_hold < self.config.min_hold_edge:
                    action = "SELL"
                    reason = f"Vender ahora domina: edge_hold={edge_hold:.4f} < min_hold_edge={self.config.min_hold_edge:.4f}."
                elif reversal_probability > self.config.max_reversal_probability:
                    action = "SELL_PARTIAL"
                    reason = f"Riesgo de reversión alto: {reversal_probability:.2%}."
                else:
                    action = "HOLD"
                    reason = f"Mantener: prob_win={prob_win:.2%}, bid={bid:.3f}, edge_hold={edge_hold:.4f}."
        else:
            best_side = None
            best_edge = None
            if edge_up is not None:
                best_side = "UP"
                best_edge = edge_up
            if edge_down is not None and (best_edge is None or edge_down > best_edge):
                best_side = "DOWN"
                best_edge = edge_down

            if best_side == "UP" and best_edge is not None and best_edge >= self.config.min_edge_entry:
                action = "BUY_UP"
                kelly = kelly_fraction_binary(p_up, up_ask or 1.0)
                reason = f"Edge UP={best_edge:.4f}. Kelly bruto={kelly:.2%}; usar Kelly fraccional si se opera."
            elif best_side == "DOWN" and best_edge is not None and best_edge >= self.config.min_edge_entry:
                action = "BUY_DOWN"
                kelly = kelly_fraction_binary(p_down, down_ask or 1.0)
                reason = f"Edge DOWN={best_edge:.4f}. Kelly bruto={kelly:.2%}; usar Kelly fraccional si se opera."

        return SignalOutput(
            timestamp=now,
            action=action,
            reason=reason,
            clean_price=clean_price,
            strike_price=strike,
            seconds_remaining=seconds_remaining,
            sigma_per_sqrt_second=sigma,
            z_score=z,
            p_up_base=p_base,
            p_up_final=p_up,
            p_down_final=p_down,
            reversal_probability=reversal_probability,
            up_bid=up_bid,
            up_ask=up_ask,
            down_bid=down_bid,
            down_ask=down_ask,
            edge_buy_up=edge_up,
            edge_buy_down=edge_down,
            edge_hold=edge_hold,
            sell_value=sell_value,
            data_age_ms=data_age_ms,
            exchange_latency_ms=latency_ms,
        )
