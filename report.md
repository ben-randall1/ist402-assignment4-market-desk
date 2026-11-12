# Assignment 4.1 — Market Data and the Dashboard

**Project:** Market Desk · IST 402 · November 12, 2026

**Repository:** [ben-randall1/ist402-assignment4-market-desk](https://github.com/ben-randall1/ist402-assignment4-market-desk)

**Submitted application commit:** [`5f21e81596e126803edc353465747751f2452db2`](https://github.com/ben-randall1/ist402-assignment4-market-desk/commit/5f21e81596e126803edc353465747751f2452db2).
This identifies the tested application, source, documentation, and demonstration evidence.
Subsequent report-only updates do not change that application version.

**Demonstration video (45 seconds):** [View/download the MP4](https://github.com/ben-randall1/ist402-assignment4-market-desk/blob/5f21e81596e126803edc353465747751f2452db2/docs/evidence/demo.mp4)
· [direct public download](https://raw.githubusercontent.com/ben-randall1/ist402-assignment4-market-desk/5f21e81596e126803edc353465747751f2452db2/docs/evidence/demo.mp4).
The video uses actual browser captures sampled once per second, with explanatory captions;
it has no narration. It shows live AAPL data (0–10s), recorded replay (10–28s), return to
live (28–32s), and a deliberate unavailable-source condition (32–45s).

## Completed work

Implemented a local Vue frontend, FastAPI backend, and persistent SQLite database.
The backend subscribes to Yahoo Finance through `yfinance.AsyncWebSocket` for AAPL and
BTC-USD, validates decoded messages, commits the observations, forms five-second candles,
and sends WebSocket snapshots to the browser. TradingView Lightweight Charts displays
updating candlesticks and corresponding observed volume deltas on a shared UTC time axis.

The dashboard identifies Yahoo Finance, live/replay mode, feed status, actual source age,
source and receipt timestamps, candle completion, and persistent receipt/version counts.
The receipt journal exposes the path back to each stored observation revision. A source
disconnect retains the chart and records, shows unavailable status, and can be reconnected.
Backend disconnection is separately visible and retried automatically.

SQLite initializes automatically on startup without credentials. Observations survive
backend restart. Receipt-prefix replay retrieves the stored stream without inventing
prices or incorporating future revisions. A small recording of 200 real Yahoo receipts
and an offline loader allow development and replay without an active market connection.

## Key design decisions

1. **Separate event time from arrival time.** Source milliseconds determine candle
   membership and OHLC order; local receipt milliseconds and increasing receipt IDs
   determine the audit trail and replay order.
2. **Preserve corrections and duplicates.** Yahoo provides no exchange event ID or
   correction sequence in this integration. The application infers identity from symbol
   and source timestamp. Each new normalized payload appends a revision. An identical
   payload appends a duplicate receipt pointing to its existing revision and cannot undo
   a newer revision. The latest previously unseen revision received wins.
3. **Recompute historical bars when needed.** Projection folds receipt prefixes, sorts
   the resulting observations by source time, and reconstructs OHLC and observed volume.
   Out-of-order observations can therefore update earlier candles correctly. Candle
   versions and their completion state are retained in SQLite. Completed intervals can
   still receive a late correction; completion does not claim exchange finality.
4. **Make provenance and failure visible.** Replay is labeled recorded. Its virtual
   clock controls interval completion, while displayed source age remains wall-clock age.
   UI refresh is never treated as proof of source freshness. No generated data silently
   replaces an unavailable live source.

## Verification results

- **10 automated tests passed**, both in the working project and against a fresh public
  repository clone. They cover duplicate/revised/old-duplicate handling, source-time
  OHLC and volume under out-of-order arrivals, missing/reset cumulative volume, completed
  candle revisions, SQLite reopen persistence, malformed quotes, replay prefixes,
  WebSocket/API integration, unavailable status, and browser Origin rejection.
  These tests use synthetic fixtures and do not establish live-provider availability.
- **Production build passed** in the workspace and after `npm ci` in the fresh clone.
- **GitHub Actions passed:** [Verify workstation run](https://github.com/ben-randall1/ist402-assignment4-market-desk/actions/runs/43277573602),
  which independently installed the locked dependencies, ran the tests, and built Vue.
- **Live-provider/browser evidence:** actual Yahoo observations reached the browser and
  SQLite. At one recorded checkpoint, the database held 346 receipts/versions (288 AAPL,
  58 BTC-USD), and SQLite integrity checking returned `ok`. Further observations arrived
  during recording. Restarting the backend retained earlier records and resumed live ingest.
- **Replay/failure evidence:** the browser visibly advanced through recorded receipt
  prefixes. A deliberate Yahoo subscription disconnect showed unavailable status while
  retaining the chart and database. The source was restored after recording.
- **Offline recording check:** the supplied 200 Yahoo receipts loaded successfully into
  a separate empty SQLite database, including from the fresh repository clone.
- **Public access:** repository and video were verified accessible; the direct video
  URL returned HTTP 200. The video is H.264, 45.00 seconds, 1280×1532.

One dependency-library deprecation warning remains in tests (`httpx`/Starlette TestClient);
it does not fail the checks. Setup, schema, and reproducibility instructions are in the README.

## Failure and revised approach

The first demo capture used the visible browser viewport. Clicking the disconnect
control scrolled the page and hid the outage banner, so that recording did not adequately
demonstrate failure behavior. Inspection of the captured frame identified the problem.
The final recording captures the entire application page, retaining the status, chart,
and journal together, and adds captions explaining receipt-prefix replay. The relevant
generated code is `project` in `backend/store.py`: it folds only the supplied receipts
before sorting by source time, so a later revision cannot appear early during replay.
The evidence log also records the initial dependency-download failure and its resolution.

## Remaining limitations

- Yahoo availability, freshness, and coverage vary. Five-second OHLC summarizes received
  quotes; it is not a guaranteed exchange-complete bar or trade tape.
- Volume is the nonnegative change between observed cumulative daily volumes, assigned
  to the later observation. First samples, missing baselines, resets, and UTC day changes
  contribute zero. Gaps are not reconstructed; crypto rolling volume further limits
  interpretation. Zero does not prove that no trading occurred.
- Same-timestamp real events can be conflated by the inferred identity. Without provider
  sequence numbers, an old payload repeated as a true retraction cannot be distinguished
  from a duplicate, and a previously unseen late payload can become the newest revision.
- Replay is accelerated receipt-order playback, not exact timing simulation or backtesting.
  Live global storage counts can continue increasing while a fixed recorded prefix replays.
- Projection currently recomputes the journal and targets small local coursework sessions.
  It uses one backend worker, with no retention policy or production throughput claim.
- The unavailable-source demonstration is a deliberate disconnect, not evidence of a
  naturally occurring Yahoo outage. Indicators, trading, backtesting, AI, and audio belong
  to subsequent assignment parts and are not implemented in Part 4.1.

## Supporting documents and evidence

- [README and startup/database initialization](https://github.com/ben-randall1/ist402-assignment4-market-desk/blob/5f21e81596e126803edc353465747751f2452db2/README.md)
- [Data flow, schema, ordering and replay design](https://github.com/ben-randall1/ist402-assignment4-market-desk/blob/5f21e81596e126803edc353465747751f2452db2/docs/design.md)
- [Agent instructions](https://github.com/ben-randall1/ist402-assignment4-market-desk/blob/5f21e81596e126803edc353465747751f2452db2/AGENTS.md)
- [AI/tool/model disclosure](https://github.com/ben-randall1/ist402-assignment4-market-desk/blob/5f21e81596e126803edc353465747751f2452db2/AI-USE.md)
- [Curated evidence log](https://github.com/ben-randall1/ist402-assignment4-market-desk/blob/main/docs/evidence.md)
- [Live dashboard](https://github.com/ben-randall1/ist402-assignment4-market-desk/blob/5f21e81596e126803edc353465747751f2452db2/docs/evidence/live-dashboard.png)
  · [recorded replay](https://github.com/ben-randall1/ist402-assignment4-market-desk/blob/5f21e81596e126803edc353465747751f2452db2/docs/evidence/replay-dashboard.png)
  · [unavailable feed](https://github.com/ben-randall1/ist402-assignment4-market-desk/blob/5f21e81596e126803edc353465747751f2452db2/docs/evidence/unavailable-dashboard.png)
- [Actual Yahoo recording](https://github.com/ben-randall1/ist402-assignment4-market-desk/blob/5f21e81596e126803edc353465747751f2452db2/docs/evidence/yahoo-recording.jsonl)
  · [tests](https://github.com/ben-randall1/ist402-assignment4-market-desk/blob/main/docs/evidence/tests.txt)
  · [production build output](https://github.com/ben-randall1/ist402-assignment4-market-desk/blob/5f21e81596e126803edc353465747751f2452db2/docs/evidence/build.txt)

AI-assisted implementation and verification are disclosed in AI-USE.md. The student
should review the generated implementation and be prepared to explain its data flow,
identity assumptions, volume calculation, replay behavior, and test results.
