from __future__ import annotations

import argparse
import asyncio

from .coinbase_feed import stream_coinbase_ticks
from .polymarket_market import stream_polymarket_books
from .polymarket_page import stream_polymarket_page
from .runtime_env import sanitize_proxy_environment
from .signal_engine import SignalConfig, SignalEngine
from .state import SharedMarketState
from .types import Position, SignalOutput


def fmt(value, decimals: int = 4) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.{decimals}f}"
    return str(value)


def print_signal(signal: SignalOutput) -> None:
    print("\n" + "=" * 110)
    print(f"{signal.timestamp:%Y-%m-%d %H:%M:%S.%f UTC}"[:-3])
    print(f"ACTION: {signal.action} | {signal.reason}")
    print(
        "BTC_clean=" + fmt(signal.clean_price, 2),
        "K=" + fmt(signal.strike_price, 2),
        "t_left=" + fmt(signal.seconds_remaining, 0),
        "sigma=" + fmt(signal.sigma_per_sqrt_second, 8),
        "z=" + fmt(signal.z_score, 3),
    )
    print(
        "p_up_base=" + fmt(signal.p_up_base, 4),
        "p_up_final=" + fmt(signal.p_up_final, 4),
        "p_down_final=" + fmt(signal.p_down_final, 4),
        "reversal=" + fmt(signal.reversal_probability, 4),
    )
    print(
        "UP bid/ask=" + fmt(signal.up_bid, 3) + "/" + fmt(signal.up_ask, 3),
        "DOWN bid/ask=" + fmt(signal.down_bid, 3) + "/" + fmt(signal.down_ask, 3),
        "edge_UP=" + fmt(signal.edge_buy_up, 4),
        "edge_DOWN=" + fmt(signal.edge_buy_down, 4),
    )
    print(
        "latency_ms=" + fmt(signal.exchange_latency_ms, 0),
        "data_age_ms=" + fmt(signal.data_age_ms, 0),
        "edge_hold=" + fmt(signal.edge_hold, 4),
        "sell_value=" + fmt(signal.sell_value, 4),
    )


async def dashboard_loop(state: SharedMarketState, engine: SignalEngine, position: Position | None, interval: float) -> None:
    while True:
        snapshot = await state.snapshot()
        signal = engine.evaluate(snapshot, position=position)
        print_signal(signal)
        await asyncio.sleep(interval)


async def main_async(args: argparse.Namespace) -> None:
    state = SharedMarketState()
    engine = SignalEngine(
        SignalConfig(
            min_edge_entry=args.min_edge,
            min_hold_edge=args.min_hold_edge,
            ewma_lambda=args.ewma_lambda,
        )
    )

    position = None
    if args.position_side and args.entry_price is not None and args.quantity is not None:
        position = Position(side=args.position_side, entry_price=args.entry_price, quantity=args.quantity)

    async def on_tick(tick):
        await state.update_btc(tick)

    async def on_book(book):
        await state.update_book(book)

    async def on_page(page):
        await state.update_page(page)

    tasks = [
        asyncio.create_task(stream_coinbase_ticks(on_tick)),
        asyncio.create_task(stream_polymarket_books(on_book, market_url=args.market_url, slug=args.slug)),
        asyncio.create_task(stream_polymarket_page(on_page, market_url=args.market_url, interval_seconds=args.page_interval, headless=not args.show_browser)),
        asyncio.create_task(dashboard_loop(state, engine, position, args.display_interval)),
    ]

    await asyncio.gather(*tasks)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="BTCUSD Polymarket 5m research monitor")
    parser.add_argument("--market-url", default=None, help="URL exacta del mercado Polymarket 5m")
    parser.add_argument("--slug", default=None, help="Slug exacto, ejemplo btc-updown-5m-1781297700")
    parser.add_argument("--display-interval", type=float, default=0.2, help="Refresh visual en segundos")
    parser.add_argument("--page-interval", type=float, default=1.0, help="Scraping visual de Polymarket en segundos")
    parser.add_argument("--show-browser", action="store_true", help="Abre navegador visible para depurar scraping")
    parser.add_argument("--min-edge", type=float, default=0.03, help="Edge minimo para entrada")
    parser.add_argument("--min-hold-edge", type=float, default=0.03, help="Edge minimo para mantener")
    parser.add_argument("--ewma-lambda", type=float, default=0.94, help="Lambda EWMA")
    parser.add_argument("--position-side", choices=["UP", "DOWN"], default=None)
    parser.add_argument("--entry-price", type=float, default=None)
    parser.add_argument("--quantity", type=float, default=None)
    return parser


def main() -> None:
    removed_proxy_vars = sanitize_proxy_environment()
    if removed_proxy_vars:
        print(f"[env] Ignorando proxies locales invalidos: {', '.join(removed_proxy_vars)}")
    args = build_parser().parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
