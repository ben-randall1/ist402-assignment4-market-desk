# Tool and model disclosure — Part 4.1

The student directed Codex in the Codex desktop app to read Assignment 4.1 and complete
the necessary work. The agent generated the initial Vue frontend, FastAPI backend,
SQLite event journal/projection, tests, startup script, CI workflow, and documentation.
The agent also used terminal tools for builds/tests and browser tools for reading the
assignment and inspecting the running application. Official yfinance, FastAPI, and
Lightweight Charts documentation informed the API integrations.

The exact serving model identifier was not exposed to this session; the agent was
identified as Codex based on GPT-6 by its environment. No additional coding agents or
delegated subagents were used. No model/provider switch occurred during implementation.
No AI service receives market data from the application in Part 4.1.

Generated code requires student review. In particular, the student should be able to
explain `backend/store.py:project`, inferred observation identity, cumulative-volume
limitations, replay's receipt prefix, and how the source age differs from UI refresh.
The curated evidence log records verification and revised approaches; this file does
not assert that the student has already personally reviewed or demonstrated every line.
