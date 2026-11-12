# Market Desk — Assignment 4.1

A local Vue + FastAPI + SQLite workstation that records Yahoo Finance WebSocket
observations, forms five-second candlesticks with corresponding observed volume deltas,
and replays the immutable receipt journal. Includes AAPL and BTC-USD; there are no orders.

## Setup and start

Requires Python 3.11+ and Node 22+. Run from the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
npm ci --prefix frontend
npm run build --prefix frontend
sh scripts/start.sh
```

Open http://127.0.0.1:8000. One FastAPI process serves the built Vue app and its
WebSocket. SQLite initializes automatically at `data/market.sqlite3`; WAL and foreign
keys are enabled. Stop with Ctrl+C. Restarting retains records. Use `MARKET_DB` to choose
another database. No credentials or API keys are required for this Yahoo connection.
Use one server worker; this coursework application is designed for localhost.

For frontend development, run the backend and `npm run dev --prefix frontend` in
another terminal, then open http://127.0.0.1:5173. Vite proxies `/api` and `/ws`.

## Use

- Choose AAPL or BTC-USD. Five-second bars provide visible candle formation during a short demo.
- The latest interval is provisional. Completion is time-based; late observations can still revise it.
- Source age is actual wall-clock age, including during replay. Source connection status is
  separate from the browser-to-backend connection. A 20-second receipt gap is marked stale.
- **Replay record** reconstructs the recorded prefix in receipt order, accelerated over
  about 40 seconds. Live recording continues; replay freezes its end cursor at launch.
  Switch back with **Live feed**. Replay never writes new observations.
- **Test feed disconnect** closes the upstream subscription and rejects new callbacks.
  The chart and database remain. **Reconnect Yahoo feed** starts a new subscription.
- Pan/zoom the chart or use **Fit chart**. All chart and journal times are UTC.

No prices are generated when the feed is unavailable. A fresh database starts with an
empty chart until Yahoo sends observations. Record during market hours, or use BTC-USD
when it is updating, then replay those recordings later.

For reproducible offline use, a small actual Yahoo recording captured November 12, 2026
is included (not generated prices). Use a separate empty database:

```sh
.venv/bin/python scripts/load_recording.py
MARKET_DB=data/replay.sqlite3 MARKET_OFFLINE=1 sh scripts/start.sh
```

Click **Replay record**. The live provider is labeled disabled/unavailable. Do not run
two backends on port 8000 at the same time. Stop the current server before switching.

## Verify

```sh
MARKET_OFFLINE=1 .venv/bin/python -m pytest -q
npm run build --prefix frontend
```

Tests use synthetic quotes only and cover duplicate/revision identity, out-of-order
OHLC, cumulative volume, interval completion, restart persistence, prefix replay,
WebSocket/API contracts, unavailable status, and origin checking. GitHub Actions runs
these checks on pushes and pull requests. Live Yahoo availability is verified separately.

Read [design and schema](docs/design.md), [evidence](docs/evidence.md),
[AI disclosure](AI-USE.md), [agent instructions](AGENTS.md), and [submission report](report.md).
SQLite data is intentionally ignored by Git; recorded evidence is curated separately.

Charts use [TradingView Lightweight Charts](https://www.tradingview.com/).
TradingView Lightweight Charts™ Copyright © 2025 TradingView, Inc.
Yahoo access uses the independent [yfinance project](https://ranaroussi.github.io/yfinance/reference/yfinance.websocket.html).

## Limits

Yahoo availability, timing, and data coverage are not guaranteed. This is an observed
quote stream, not an exchange-complete trade tape. Five-second OHLC is calculated from
received quotes. Volume is a nonnegative difference of Yahoo cumulative daily volume,
assigned to the later observation; the first sample, missing baseline, resets and UTC
day changes contribute zero. Gaps cannot be recovered. Crypto volume may be a rolling
measure, so its deltas are only an observation proxy. Zero does not establish no trading.
Revisions have no provider sequence: the last previously unseen payload received for
an inferred identity wins. Same-timestamp distinct real events may be conflated.
The backend recomputes projections from the journal and is intended for coursework-sized
recordings; it has no retention policy or production throughput guarantees.
