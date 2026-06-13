from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from datetime import timezone

import websockets

from .time_utils import parse_exchange_time, utc_now
from .types import BtcTick

COINBASE_WS_URL = "wss://ws-feed.exchange.coinbase.com"
PRODUCT_ID = "BTC-USD"
TickHandler = Callable[[BtcTick], Awaitable[None]]


async def stream_coinbase_ticks(
    on_tick: TickHandler,
    product_id: str = PRODUCT_ID,
    ws_url: str = COINBASE_WS_URL,
) -> None:
    """Stream Coinbase ticker ticks and emit normalized BtcTick objects."""
    subscribe_message = {
        "type": "subscribe",
        "product_ids": [product_id],
        "channels": ["ticker", "heartbeat"],
    }

    while True:
        try:
            async with websockets.connect(ws_url, ping_interval=20) as websocket:
                await websocket.send(json.dumps(subscribe_message))

                async for raw_message in websocket:
                    message = json.loads(raw_message)
                    if message.get("type") != "ticker":
                        continue

                    price = float(message["price"])
                    exchange_time = parse_exchange_time(message["time"])
                    if exchange_time.tzinfo is None:
                        exchange_time = exchange_time.replace(tzinfo=timezone.utc)
                    received_at = utc_now()

                    await on_tick(
                        BtcTick(
                            price=price,
                            exchange_time=exchange_time,
                            received_at=received_at,
                            product_id=product_id,
                        )
                    )
        except (websockets.ConnectionClosed, OSError, asyncio.TimeoutError) as exc:
            print(f"[coinbase] Conexion perdida: {exc}. Reintentando en 1s...")
            await asyncio.sleep(1.0)
