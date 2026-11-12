import asyncio
import contextlib
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

import yfinance as yf
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.staticfiles import StaticFiles
from .store import Store, SOURCE

SYMBOLS = ["AAPL", "BTC-USD"]


class Feed:
    def __init__(self, store):
        self.store = store
        self.state = "connecting"
        self.detail = "Connecting to Yahoo Finance"
        self.last_receipt = None
        self.paused = False

    async def run(self):
        while True:
            if self.paused:
                await asyncio.sleep(1)
                continue
            self.state, self.detail = "connecting", "Opening Yahoo Finance WebSocket"
            try:
                async with yf.AsyncWebSocket(verbose=False) as stream:
                    await stream.subscribe(SYMBOLS)
                    self.state, self.detail = "waiting", "Subscribed; waiting for a source observation"

                    async def receive(message):
                        if self.paused:
                            return
                        try:
                            if message.get("id") not in SYMBOLS:
                                return
                            self.store.ingest(message)
                            self.last_receipt = int(time.time()*1000)
                            self.state, self.detail = "live", "Receiving Yahoo Finance observations"
                        except (ValueError, KeyError, TypeError, OverflowError):
                            self.detail = "Rejected an invalid provider observation"

                    listener = asyncio.create_task(stream.listen(receive))
                    try:
                        while not self.paused and not listener.done():
                            await asyncio.sleep(1)
                        if listener.done():
                            listener.result()
                            raise ConnectionError("Provider listener ended")
                    finally:
                        listener.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await listener
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.state = "unavailable"
                self.detail = f"Yahoo connection failed ({type(exc).__name__}); retrying in 5s"
                await asyncio.sleep(5)

    def status(self):
        if self.paused:
            return {"state": "unavailable", "detail": "Feed disconnected deliberately for failure demonstration"}
        result = {"state": self.state, "detail": self.detail}
        if self.last_receipt and time.time()*1000-self.last_receipt > 20000:
            result = {"state": "stale", "detail": "No new source observation for over 20 seconds"}
        return result


def create_app(db_path=None, live=True):
    store = Store(db_path or os.getenv("MARKET_DB", "data/market.sqlite3"))
    feed = Feed(store)
    if not live:
        feed.state, feed.detail = "unavailable", "Live provider disabled; use Replay record for stored observations"

    @asynccontextmanager
    async def lifespan(app):
        task = asyncio.create_task(feed.run()) if live else None
        yield
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        store.db.close()

    app = FastAPI(title="Market Desk", lifespan=lifespan)
    app.state.store, app.state.feed = store, feed

    def snapshot(symbol, through=None):
        events = store.events(through)
        replay_clock = events[-1]["receipt_ms"] if through is not None and events else None
        bars = store.candles(through=through, clock_ms=replay_clock)
        selected = [b for b in bars if b["symbol"] == symbol][-500:]
        symbol_events = [e for e in events if e["symbol"] == symbol]
        newest = max(symbol_events, key=lambda e:e["source_ms"], default=None)
        return {"type": "snapshot", "mode": "replay" if through is not None else "live",
                "symbol": symbol, "source": SOURCE, "interval": 5, "candles": selected,
                "feed": {**feed.status(), "enabled": live}, "stats": store.stats(), "server_ms": int(time.time()*1000),
                "source_ms": newest["source_ms"] if newest else None,
                "receipt_ms": symbol_events[-1]["receipt_ms"] if symbol_events else None,
                "replay_clock_ms": replay_clock, "cursor": through,
                "recent": [{k:e[k] for k in ("receipt_id","revision_id","source_ms","receipt_ms","price","version","disposition")} for e in symbol_events[-6:][::-1]]}

    @app.get("/api/status")
    def status():
        return {"feed": feed.status(), "stats": store.stats(), "symbols": SYMBOLS}

    @app.get("/api/candles")
    def candles(symbol: str = "AAPL", through: int | None = Query(None, ge=0)):
        return snapshot(symbol, through)

    @app.get("/api/observations")
    def observations(after: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000)):
        return [e for e in store.events() if e["receipt_id"] > after][:limit]

    @app.websocket("/ws")
    async def socket(ws: WebSocket):
        # Local control channel: reject cross-site browser clients.
        origin = ws.headers.get("origin", "")
        if origin and origin not in ("http://127.0.0.1:8000", "http://localhost:8000", "http://localhost:5173", "http://127.0.0.1:5173"):
            await ws.close(code=1008)
            return
        await ws.accept()
        symbol, replay, cursor = "AAPL", False, 0
        end_cursor = 0
        try:
            while True:
                if not replay:
                    store.materialize()
                packet = snapshot(symbol, cursor if replay else None)
                packet["replay_end"] = end_cursor
                packet["replay_finished"] = replay and cursor >= end_cursor
                await ws.send_json(packet)
                try:
                    command = await asyncio.wait_for(ws.receive_json(), timeout=0.4 if replay else 1)
                    if command.get("symbol") in SYMBOLS:
                        symbol = command["symbol"]
                    action = command.get("action")
                    if action == "replay":
                        end_cursor = max((e["receipt_id"] for e in store.events()), default=0)
                        replay, cursor = True, 0
                    elif action == "live":
                        replay = False
                    elif action == "disconnect":
                        feed.paused = True
                    elif action == "reconnect":
                        feed.paused = False
                except asyncio.TimeoutError:
                    if replay:
                        cursor = min(end_cursor, cursor + max(1, end_cursor//100))
        except (WebSocketDisconnect, RuntimeError):
            pass

    dist = Path(__file__).resolve().parent.parent / "frontend/dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return app


app = create_app(live=os.getenv("MARKET_OFFLINE") != "1")
