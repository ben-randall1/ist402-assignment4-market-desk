# Assignment 4 agent instructions

Build this cumulative IST 402 assignment as a local Vue / FastAPI / SQLite application.
Part 4.1 covers Yahoo live data, candles and corresponding volume, persistence, replay,
and observable failure behavior. Do not represent fixtures or recordings as live data.
Do not add trading, AI providers, or audio before the relevant assignment part.

Preserve the receipt journal and all distinct observation revisions. Never silently
overwrite source or receipt timestamps. Keep source-time sorting separate from receipt-order
replay. Yahoo has no exchange event identifier here; document inferred identity limitations.
Keep data age, provider status, provisional candles, and replay mode visible.

Run `MARKET_OFFLINE=1 .venv/bin/python -m pytest -q` and
`npm run build --prefix frontend` after functional changes. Inspect the running browser
for chart rendering, replay, and source-unavailable states. Record actual results in
`docs/evidence.md`, distinguishing synthetic tests from live observations.

Keep README.md, docs/design.md, AI-USE.md, and report.md consistent with the implementation.
Never commit credentials, .env, SQLite runtime databases, private course content, or dependencies.
Canvas accepts only report.md; source and evidence belong in GitHub. Identify missing
submission requirements honestly. Do not claim a test, video, or publication exists until verified.
