# Design and data contract

## Data flow

Yahoo Finance → `yfinance.AsyncWebSocket` → validate/normalize → SQLite transaction
(`revisions` + `receipts`) → source-time projection → versioned five-second candles
→ FastAPI `/ws` snapshots → Vue → Lightweight Charts candlestick and volume series.
The commit precedes browser publication; the journal remains usable after restart.
The server sends snapshots every second; a refreshed UI does not imply fresh source data.

The frontend takes sorted unique candle timestamps and calls `setData`, allowing
corrections to historical candles as well as updates to the current candle. Price and
volume share a time axis. Volume overlays the bottom of the chart on a separate scale.
The interface borrows the familiar instrument/price/OHLC/chart hierarchy of financial
workstations, with added source-age and persistence evidence visible beside the chart.

## SQLite schema (created automatically by Store)

| Table | Key / fields | Purpose |
| --- | --- | --- |
| revisions | integer id; symbol, source_ms, source, version, fingerprint, price, day_volume, raw_json | Distinct normalized payload versions; unique `(symbol,source_ms,fingerprint)` and `(symbol,source_ms,version)` |
| receipts | integer id; revision_id FK, receipt_ms, disposition | Append-only receipt order, including duplicates; links back to original raw provider payload |
| candle_versions | integer id; symbol, start_s, interval_s, version, complete, recorded_ms, candle_json | Persisted materialized revisions, including interval completion; unique `(symbol,start_s,interval_s,version)` |

All timestamps are Unix UTC milliseconds except candle `start_s` / chart `time` in
seconds. `raw_json` is the decoded Yahoo message, not raw network frames. Fingerprints
use normalized symbol/source time/price/day volume; unrelated message fields do not
create a price revision. Source is constant Yahoo Finance WebSocket in this database.
The current candle is the highest materialized version, or the deterministic projection
of the journal. Its JSON includes OHLC, volume, source/receipt times, observation count,
and completion. Materialized candle versions are refreshed by the active dashboard
connection; after a restart they are refreshed when the dashboard reconnects.

## Identity, corrections, and ordering

Yahoo messages in this integration lack an exchange event ID/revision sequence. Infer
observation identity from `(symbol, source_ms)`. A matching normalized fingerprint is a
duplicate: append a receipt pointing to the existing revision but do not count it twice
or roll back a correction. A distinct payload at that identity appends version N+1.
Last distinct version received wins. This is a documented application policy, not proof
of Yahoo correction semantics. A true retraction to an already seen payload is
indistinguishable from a duplicate and therefore does not roll back.

For projection, fold receipts to the latest distinct revision per inferred identity,
then sort by symbol and source time. Bucket source times into half-open five-second
intervals. Open/close follow earliest/latest source time, high/low use extrema, and
volume uses consecutive cumulative-volume deltas with reset/missing/day guards.
An out-of-order quote recomputes its affected historical OHLC and downstream volume.
Completed candles can have additional versions after a late quote or correction.
No empty intervals or missing quotes are invented.

## Replay and time

`/api/candles?through=N` and replay use only receipt IDs at or below N. They never
consult future revisions when folding that prefix. Completion uses the last included
receipt timestamp as a virtual clock; the age label still shows real wall-clock age.
Replay begins at receipt zero and advances a bounded number of receipts every 400ms.
It freezes the final cursor while live ingest continues. This is accelerated recorded
observation playback, not historical backtesting or an exact inter-arrival-time simulation.

## Failure and boundaries

Yahoo exceptions set unavailable status and retry after five seconds. Subscription with
no quotes is waiting; after a prior quote, a 20-second receive gap is stale. Transport
connectivity cannot prove source freshness, so the selected symbol's source age remains
visible independently. The manual disconnect control closes the Yahoo listener, drops
pending callbacks, and shows a labeled demonstration outage. Browser socket failure
shows disconnected, retains the last chart, and reconnects every two seconds.

Bind to 127.0.0.1 and use a single worker. The local WebSocket checks browser Origins.
No provider credentials are used. Revisions and runtime databases contain market quotes,
not account/order data. No real or simulated trading is implemented in Part 4.1.

References: [yfinance streaming API](https://ranaroussi.github.io/yfinance/reference/yfinance.websocket.html),
[FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/),
[Lightweight Charts API](https://tradingview.github.io/lightweight-charts/docs).
