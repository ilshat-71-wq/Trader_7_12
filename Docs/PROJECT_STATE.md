# TRADER_7_12 PRO — PROJECT STATE

## CANONICAL CURRENT STATE — READ THIS FIRST

This file is the single source of truth for the **current technical state** of Trader_7_12 Pro.

- Product architecture and goals: `Docs/PROJECT_PASSPORT_v2.md`
- Current technical state and next action: this file
- Obsolete handoff/cleanup documents are intentionally not used.

## Checkpoint
Date: 2026-08-16
Branch: `agent/futures-expiry-liquidity`
Repository: `ilshat-71-wq/Trader_7_12`
Latest published commit: `1584327` — `Use IMOEX2 and IRUS2 for historical relative strength`

## Product contract
Trader_7_12 Pro is a scanner/trading assistant for intraday MOEX futures.

The user trades futures as the execution instrument and analyzes the underlying SPOT asset first. The assistant evaluates the market, finds where money/activity is concentrated, identifies strong and weak liquid instruments, considers benchmark-relative strength, trend, levels and setup, confirms the idea with the corresponding futures, and presents only the best 2–3 candidates.

The user makes the final decision on entry, position size, risk, SL/TP and execution.

## Target benchmark
Primary benchmark: **IMOEX2 / IRUS2 full-return market benchmark** when genuinely available from BCS.

Current BCS verification on 2026-08-16:
- `IMOEX2` — found, MOEX index, class `INDX`.
- `IMOEX` — found, MOEX index, class `INDX`.
- `IMOEXF` — found, futures, class `SPBFUT`.
- `IRUS2` — not returned by ticker lookup.

Current hard rule:
- prefer `IMOEX2 / IRUS2`;
- never silently substitute ordinary `IMOEX` or `IMOEXF`;
- if the correct benchmark cannot be resolved, RS must be reported as unavailable rather than fabricated.

The historical service now uses `RS_TICKERS = ("IMOEX2", "IRUS2")` and this change is committed in `1584327`.

## Target architecture
`DYNAMIC FUTURES UNIVERSE`
→ `FUTURES → SPOT MAPPING`
→ `SPOT LIQUIDITY / PRICE×VOLUME`
→ `SPOT DAILY TREND`
→ `RELATIVE STRENGTH / WEAKNESS vs IMOEX2 / IRUS2`
→ `LOCAL LEVELS / PREVIOUS HIGHS / LOWS`
→ `SETUP: BREAKOUT / PULLBACK / REBOUND`
→ `FUTURES CONFIRMATION`
→ `QUALITY RANKING`
→ `TOP 2–3`
→ `USER DECIDES`

## Scanner-only boundary
Must NOT reintroduce:
- risk management engine;
- deposit/risk percentage logic;
- position sizing or lot calculation;
- automatic SL/TP;
- order execution;
- portfolio management;
- automatic trade management.

Historical replay is READ ONLY and must never place orders.

## Core services retained
- `Program/services/futures_universe_service.py`
- `Program/services/futures_spot_mapping_service.py`
- `Program/services/futures_morning_radar_service.py`
- `Program/services/futures_confirmation_service.py`
- `Program/services/futures_trade_candidate_service.py`
- `Program/services/morning_trading_pipeline_service.py`
- `Program/services/morning_scanner_runner.py`
- `Program/services/historical_candidate_ranker_service.py`
- `Program/services/historical_universe_replay_service.py`
- `Program/services/historical_universe_replay_runner.py`
- `Program/services/historical_replay_report.py`
- supporting market-data services required by the above.

## Cleanup status
The repository has been reduced toward a scanner-only architecture. Obsolete legacy scanner/signal/rating/volume/portfolio/risk/manual diagnostic layers have been removed where they were no longer required.

Cleanup is dependency-aware: before deleting any additional service, inspect imports and runtime/history dependencies first.

Temporary cleanup documentation is not part of the canonical project context and has been removed. Only the passport and this state file remain as project-context documents.

## Verification completed today
- Core compile: PASS.
- `test_futures_confirmation_service.py`: ALL TESTS PASSED.
- `test_morning_trading_pipeline_service.py`: ALL TESTS PASSED after updating the stale test contract.
- `test_historical_universe_replay_service.py`: PASS.
- `test_momentum_service.py`: PASS.
- BCS authorization: PASS.
- BCS benchmark metadata check completed.

## Historical replay
Persistent replay results and offline reporting were added and published in `2c2e763`.

Runtime results are stored under `Docs/historical_replay/` and ignored by Git.

Recent 4-day diagnostic replay (2026-08-11 through 2026-08-14):
- 12 candidates;
- 8 available outcomes;
- directional win rate 37.5%;
- average directional return -0.81%;
- average MFE 0.04%.

These are diagnostic historical results, not a profitability guarantee.

## UI direction
The UI is scanner-first, Russian-language, visually clear and designed around large numbers and strong highlighting of the 2–3 best active instruments.

The main screen should make the following visible within seconds:
- market direction;
- strongest/weakest instruments;
- where the money is;
- `PRICE × VOLUME`;
- SPOT direction/strength;
- important levels;
- setup;
- futures confirmation;
- final TOP 2–3.

## Live-market validation
Sunday 2026-08-16 has no regular trading session. Do not invent live results.

Next live validation: the next trading morning from **07:00 Moscow time**.

Validation sequence:
1. confirm BCS authorization/data;
2. confirm market benchmark;
3. observe dynamic universe;
4. verify current-day liquidity and `price × volume`;
5. verify strong/weak ranking versus the market;
6. inspect levels and setups;
7. verify futures confirmation;
8. check that TOP 2–3 are genuinely active and liquid;
9. record any false positives/false negatives before changing filters.

## NEXT ACTION
**Next trading morning: run the live scanner from 07:00 Moscow time and evaluate the real candidate output before making further algorithmic changes.**

Do not loosen filters merely to force candidates. If no candidate appears, identify the exact blocking condition first.

## Git rule
`origin/agent/futures-expiry-liquidity` is the source of truth.

Workflow:
1. inspect HEAD/status;
2. make the smallest justified change;
3. compile;
4. run the relevant test/replay;
5. commit;
6. push;
7. verify the remote branch.

## New-chat transfer rule
Start every continuation by reading:
1. `Docs/PROJECT_PASSPORT_v2.md`
2. `Docs/PROJECT_STATE.md`

Then inspect Git HEAD/status and continue from `NEXT ACTION` in this file.

Do not redesign the project from memory and do not restore removed architecture without explicit justification.