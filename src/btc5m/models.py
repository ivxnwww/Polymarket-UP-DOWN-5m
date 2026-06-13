from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

import numpy as np

EPS = 1e-12


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def norm_cdf(x: float) -> float:
    """Standard normal cumulative distribution without scipy."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def safe_logit(p: float) -> float:
    p = clamp(p, 1e-6, 1.0 - 1e-6)
    return math.log(p / (1.0 - p))


def sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


@dataclass(slots=True)
class EWMAVolatility:
    """EWMA estimator for log-return variance per second.

    If ticks arrive irregularly, instantaneous variance is r^2 / dt, where
    r = ln(S_t / S_{t-1}) and dt is measured in seconds.
    The resulting sigma is expressed in log-return units per sqrt(second).
    """

    lam: float = 0.94
    variance_per_second: float | None = None
    last_price: float | None = None
    last_time: datetime | None = None

    def update(self, price: float, observed_at: datetime) -> float | None:
        if price <= 0:
            return self.sigma

        if self.last_price is None or self.last_time is None:
            self.last_price = price
            self.last_time = observed_at
            return self.sigma

        dt = max(EPS, (observed_at - self.last_time).total_seconds())
        r = math.log(price / self.last_price)
        inst_var = (r * r) / dt

        if self.variance_per_second is None:
            self.variance_per_second = inst_var
        else:
            self.variance_per_second = self.lam * self.variance_per_second + (1.0 - self.lam) * inst_var

        self.last_price = price
        self.last_time = observed_at
        return self.sigma

    @property
    def sigma(self) -> float | None:
        if self.variance_per_second is None:
            return None
        return math.sqrt(max(0.0, self.variance_per_second))


@dataclass(slots=True)
class KalmanPriceVelocity:
    """Small 1D Kalman filter with state [price, velocity].

    This does not make the feed faster. It smooths noisy observations and
    estimates short-term velocity so the signal engine can avoid reacting to a
    single bad tick.
    """

    process_var: float = 5.0
    measurement_var: float = 25.0
    price: float | None = None
    velocity: float = 0.0
    p00: float = 1.0
    p01: float = 0.0
    p10: float = 0.0
    p11: float = 1.0
    last_time: datetime | None = None

    def update(self, observed_price: float, observed_at: datetime) -> tuple[float, float]:
        if self.price is None or self.last_time is None:
            self.price = observed_price
            self.velocity = 0.0
            self.last_time = observed_at
            return self.price, self.velocity

        dt = max(EPS, (observed_at - self.last_time).total_seconds())

        # Predict state: x = F x, F = [[1, dt], [0, 1]]
        pred_price = self.price + self.velocity * dt
        pred_velocity = self.velocity

        # Predict covariance: P = FPF' + Q
        q = self.process_var
        p00 = self.p00 + dt * (self.p10 + self.p01) + dt * dt * self.p11 + q * dt * dt
        p01 = self.p01 + dt * self.p11
        p10 = self.p10 + dt * self.p11
        p11 = self.p11 + q * dt

        # Update with measurement z = price + noise
        y = observed_price - pred_price
        s = p00 + self.measurement_var
        k0 = p00 / s
        k1 = p10 / s

        self.price = pred_price + k0 * y
        self.velocity = pred_velocity + k1 * y

        self.p00 = (1.0 - k0) * p00
        self.p01 = (1.0 - k0) * p01
        self.p10 = p10 - k1 * p00
        self.p11 = p11 - k1 * p01
        self.last_time = observed_at

        return self.price, self.velocity


def terminal_probability_up(
    price: float,
    strike: float,
    seconds_remaining: float,
    sigma_per_sqrt_second: float,
    mu_per_second: float = 0.0,
) -> float:
    """P(S_T > K) under a lognormal/Brownian short-horizon model.

    log(S_T/S_t) ~ Normal((mu - 0.5*sigma^2)*tau, sigma^2*tau)
    tau is measured in seconds; sigma is log-return volatility per sqrt(second).
    """
    if price <= 0 or strike <= 0:
        return 0.5
    if seconds_remaining <= 0:
        return 1.0 if price > strike else 0.0
    if sigma_per_sqrt_second <= 0:
        return 1.0 if price > strike else 0.0 if price < strike else 0.5

    tau = seconds_remaining
    numerator = math.log(price / strike) + (mu_per_second - 0.5 * sigma_per_sqrt_second**2) * tau
    denominator = sigma_per_sqrt_second * math.sqrt(tau)
    return clamp(norm_cdf(numerator / denominator))


def z_score_to_strike(
    price: float,
    strike: float,
    seconds_remaining: float,
    sigma_per_sqrt_second: float,
) -> float | None:
    """Distance to strike divided by expected remaining move.

    Positive z favors UP. Negative z favors DOWN.
    """
    if price <= 0 or strike <= 0 or seconds_remaining <= 0 or sigma_per_sqrt_second <= 0:
        return None
    expected_move_abs = price * sigma_per_sqrt_second * math.sqrt(seconds_remaining)
    if expected_move_abs <= EPS:
        return None
    return (price - strike) / expected_move_abs


def first_passage_probability_cross_strike(
    price: float,
    strike: float,
    seconds_remaining: float,
    sigma_per_sqrt_second: float,
) -> float:
    """Approximate probability of touching/crossing the strike before expiry.

    Uses the reflection-principle approximation for zero-drift Brownian motion
    in log-price space:
        P(hit barrier before T) ~= 2 * [1 - Phi(distance/(sigma*sqrt(T)))]

    This is a risk metric, not a settlement probability. If price is already at
    the barrier, the crossing probability is 1.
    """
    if price <= 0 or strike <= 0:
        return 1.0
    if seconds_remaining <= 0:
        return 0.0
    if sigma_per_sqrt_second <= 0:
        return 1.0 if abs(price - strike) <= EPS else 0.0

    distance = abs(math.log(price / strike))
    scale = sigma_per_sqrt_second * math.sqrt(seconds_remaining)
    if scale <= EPS:
        return 0.0
    p = 2.0 * (1.0 - norm_cdf(distance / scale))
    return clamp(p)


def expected_value_buy(prob_win: float, ask_price: float) -> float:
    """EV per $1 payout share when buying at ask_price."""
    return prob_win - ask_price


def expected_value_hold(prob_win: float, current_bid: float) -> float:
    """Incremental value of holding instead of selling now."""
    return prob_win - current_bid


def kelly_fraction_binary(prob_win: float, entry_price: float) -> float:
    """Kelly fraction for a binary contract bought at price q with payout 1.

    f* = (p - q) / (1 - q)
    Positive means allocate; negative means no bet. In practice use fractional
    Kelly, e.g. 0.25 * f*, because p is an estimate and can be wrong.
    """
    if entry_price >= 1.0:
        return 0.0
    return (prob_win - entry_price) / max(EPS, 1.0 - entry_price)


def monte_carlo_terminal_probability_up(
    price: float,
    strike: float,
    seconds_remaining: float,
    sigma_per_sqrt_second: float,
    mu_per_second: float = 0.0,
    paths: int = 20_000,
    seed: int | None = None,
) -> float:
    """Monte Carlo estimate for P(S_T > K).

    Uses one-step terminal sampling, not full path simulation. It is fast and
    appropriate when only terminal direction matters.
    """
    if seconds_remaining <= 0:
        return 1.0 if price > strike else 0.0
    if sigma_per_sqrt_second <= 0:
        return 1.0 if price > strike else 0.0 if price < strike else 0.5

    rng = np.random.default_rng(seed)
    tau = seconds_remaining
    shocks = rng.normal(0.0, 1.0, size=paths)
    log_returns = (mu_per_second - 0.5 * sigma_per_sqrt_second**2) * tau + sigma_per_sqrt_second * math.sqrt(tau) * shocks
    terminal_prices = price * np.exp(log_returns)
    return float(np.mean(terminal_prices > strike))
