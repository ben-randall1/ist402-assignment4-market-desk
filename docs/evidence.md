# Curated evidence log — Assignment 4.1

Recorded November 12, 2026. This is selected development evidence, not a full chat export.
No credentials or private Canvas content are included in the repository.

## 1. Required scope → implementation

- Instruction excerpt: “read assignment 4.1 and complete the necessary steps.” The agent
  read the Part 4.1 page and Assignment 4 overview in the authenticated course browser.
- Decision: use the required local Vue / FastAPI / SQLite stack. Implement live Yahoo
  WebSocket ingest, five-second OHLC, corresponding observed volume, and an audit trail.
- Generated files: [backend/main.py](../backend/main.py), [backend/store.py](../backend/store.py),
  [App.vue](../frontend/src/App.vue), [design/schema](design.md).
- Observation: the running Vue page displayed AAPL prices supplied by Yahoo, source age
  around 1–4 seconds, changing OHLC, volume bars, and increasing persistent receipt counts.
- Uncertainty: feed timing/coverage is provider-dependent; these are observed quotes,
  not exchange-complete bars. Same-timestamp messages are inferred revisions.

## 2. Dependency download failure → network-enabled setup

- Question: can the empty workspace build and run the required dependencies?
- First result: pip/npm could not resolve registry hostnames inside the restricted
  network environment. This was a setup failure, not a Yahoo market outage.
- Decision: rerun dependency installation with approved network access; isolate Python
  dependencies in `.venv`, keep npm dependencies local, and lock resolved versions.
- Verification: [production build output](evidence/build.txt) succeeds. No credentials
  were introduced. [requirements.txt](../requirements.txt) and the npm lockfile preserve versions.

## 3. Identity and replay → automated checks

- Instruction excerpt: preserve observation identity, timestamps, revisions, and completion;
  explain and test duplicates, revised observations, and out-of-order observations.
- Generated code: `project` in [store.py](../backend/store.py) first folds receipt prefixes
  to latest distinct revisions, then sorts by source time before forming OHLC. A previously
  seen fingerprint is a duplicate receipt, so it cannot undo a newer distinct revision.
- Verification: [10 passing tests](evidence/tests.txt). Tests cover duplicate/revised/old
  duplicate sequences; receipt-prefix replay; late OHLC and volume; missing/reset volume;
  completion revisions; database reopen; malformed quotes; WebSocket/API flow; an unavailable
  feed; and rejected cross-site browser Origins. Test prices are synthetic fixtures.
- Decision: keep receipt order separate from candle source-time order, and disclose the
  inferred-identity and repeated-payload/retraction ambiguity instead of claiming provider IDs.
- Limitation: local tests do not establish Yahoo uptime or exact exchange correctness.

## 4. Live Yahoo → database → browser

- Live session began around 13:00 Eastern (18:00 UTC), November 12, 2026.
- [Live dashboard screenshot](evidence/live-dashboard.png) shows real Yahoo data,
  the chart, source/receipt times, SQLite totals, and revision journal.
- A direct SQLite check returned `integrity_check=ok`, 346 receipts and 346 distinct
  payload versions: 288 AAPL versions and 58 BTC-USD versions at that checkpoint.
  Source timestamps span 18:00:42–18:05:39 UTC; [database summary](evidence/live-database-check.json)
  preserves the exact range. Counts continued increasing during subsequent recording.
- [200 actual Yahoo receipts](evidence/yahoo-recording.jsonl) were exported with original
  decoded messages and receipt timestamps for reproducible offline replay. The loader
  successfully imported all 200 into a separate empty SQLite database.
- Uncertainty: observed cumulative volume deltas do not reconstruct gaps or prove full
  interval exchange volume. BTC-USD cumulative/rolling volume has additional limitations.

## 5. Video framing failure → revised capture

- First attempt: 50 sampled viewport frames. Clicking a control scrolled the browser,
  hiding the source-unavailable banner from the frame. This was unsuitable evidence.
- Decision: discard that video attempt and capture the complete application page at
  one observed frame per second. Add explanatory captions, then encode those frames
  as a 45-second MP4. Repeated frames make the output 10 fps; no prices are generated.
- Final evidence: [45-second demonstration video](evidence/demo.mp4), [replay screenshot](evidence/replay-dashboard.png),
  [unavailable-feed screenshot](evidence/unavailable-dashboard.png).
- The final video shows live AAPL candles/volume (0–10s), accelerated receipt-prefix
  replay (10–28s), return to live (28–32s), and a deliberate source disconnect (32–45s).
  Captions identify the no-future-revisions design decision. There is no narration/audio.
- Verified media metadata: H.264, 1280×1532, 45.00 seconds, 10 fps. The source was restored
  after recording. The deliberate disconnect is distinguished from an organic Yahoo failure.

## 6. Publication and reproducibility

- User authorized creating a new public repository. GitHub browser creation succeeded at
  [ben-randall1/ist402-assignment4-market-desk](https://github.com/ben-randall1/ist402-assignment4-market-desk).
- Source, docs, tests, selected screenshots, recorded quotes, and video are kept in GitHub;
  local databases, dependencies, credentials, and course pages are excluded.
- Final publication/clean-checkout verification is recorded in the submission report.
- Published application commit: `5f21e81596e126803edc353465747751f2452db2`.
  A fresh clone installed frontend packages with `npm ci` and produced a successful
  build; all 10 tests passed when run from its repository root using the existing
  locked Python environment. The 200-receipt loader also succeeded in that clone.
- The first clean-clone test invocation accidentally ran from the parent directory and
  failed to import `backend`. Running the documented command from the repository root
  resolved it; no application code change was needed.
- [GitHub Actions run 43277573602](https://github.com/ben-randall1/ist402-assignment4-market-desk/actions/runs/43277573602)
  completed successfully with independent dependency installation, tests, and build.
- The direct public MP4 URL returned HTTP 200. After a backend restart, the browser
  displayed stored historical bars plus new live Yahoo observations and 839 receipts
  at the verification checkpoint. This supports persistence across a real process restart.
