# TRADER_7_12 PRO — PROJECT STATE

## Purpose
Technical state checkpoint for continuing Trader_7_12 Pro safely across chats. This file describes **where the repository is now**, not the full product idea. The product idea and non-negotiable architecture live in `Docs/PROJECT_PASSPORT_v2.md`.

## Checkpoint
Date: 2026-08-16
Branch: `agent/futures-expiry-liquidity`
Known HEAD at checkpoint: `90a0219`
Repository: `ilshat-71-wq/Trader_7_12`

## Product contract
Trader_7_12 Pro is a scanner/trading assistant for intraday MOEX futures.

The user trades futures, using the underlying SPOT asset as the primary analytical source because futures are the execution instrument with lower commissions. The assistant does not execute trades and does not decide position size, SL, TP, or risk.

Primary market benchmark: full-return IMOEX2 / IRUS2 when actually available from BCS. Never fabricate RS and never silently replace the benchmark with ordinary IMOEX or IMOEXF.

Main user workflow:
1. Evaluate the market and identify the current market direction.
2. Find the most active/liquid instruments where the money is concentrated today.
3. Evaluate SPOT strength/weakness versus the benchmark.
4. Consider daily trend, intraday movement, local levels/highs/lows and setup.
5. Use the futures as confirmation.
6. Rank and highlight only the best 2–3 futures candidates.
7. User opens the chart and makes the final entry decision.

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
- supporting market-data services required by the above, including `candle_service.py`, `history_candle_service.py`, and `trade_service.py`.

## Cleanup completed
Obsolete legacy scanner/signal/rating/volume/portfolio/risk/manual diagnostic layers have been removed from the active architecture where they were no longer required. Cleanup must remain conservative: before deleting a service, check imports and historical/runtime dependencies.

## Current benchmark verification
BCS lookup on 2026-08-16:
- `IMOEX2` found as MOEX index, class `INDX`.
- `IMOEX` found as MOEX index, class `INDX`.
- `IMOEXF` found as futures, class `SPBFUT`.
- `IRUS2` was not returned by the ticker lookup.

Current rule: target benchmark is `IMOEX2 / IRUS2`; ordinary `IMOEX` / `IMOEXF` must not be used as silent substitutes.

## Current local change
`Program/services/historical_universe_replay_service.py` has an uncommitted local edit changing the historical benchmark priority from `IMOEX/IMOEX2` to `IMOEX2/IRUS2`.

This edit has passed `py_compile` and the historical replay service test, but has not yet been committed at this checkpoint.

## Verification already completed
- Core compile: PASS.
- `test_futures_confirmation_service.py`: ALL TESTS PASSED.
- `test_historical_universe_replay_service.py`: PASS.
- `test_momentum_service.py`: PASS.

## Known issue to fix next
`Program/test_morning_trading_pipeline_service.py` currently fails because it still expects obsolete `pipeline_version == "0.3"`.

Failure observed:
`AssertionError` in `test_pipeline_returns_candidate`.

This is an outdated test contract and must be reviewed against the current scanner-only pipeline. Do NOT blindly restore old version semantics merely to make the test green.

Next action:
1. inspect current `morning_trading_pipeline_service.py` output contract;
2. update the test to validate current behavior rather than obsolete version text;
3. rerun the pipeline test and the full core verification set;
4. only then commit/push the benchmark edit and state checkpoint.

## Historical replay checkpoint
Recent 4-day replay (2026-08-11 through 2026-08-14) produced 12 candidates and 8 available outcomes in the saved replay.
Observed quick summary:
- DIR WIN RATE: 37.5%
- AVG DIR: -0.81%
- AVG MFE: 0.04%

This is diagnostic evidence only, not a production profitability claim. The result also contains network `SSLError` retries during historical data access. Do not change trading logic solely because of transient network errors.

Saved replay results are runtime artifacts under `Docs/historical_replay/` and are ignored by Git.

## UI direction
The UI should be scanner-first, Russian-language, visually clear, with large numbers and strong highlighting of the 2–3 best active instruments. The user wants to see where the money is (`price × volume`), market direction, strong/weak instruments, levels, and the futures to inspect. Avoid dense legacy trading-terminal presentation.

## Git rule
GitHub branch `origin/agent/futures-expiry-liquidity` is the source of truth. Make minimal changes, compile, run the relevant test/replay, then commit and push.

## Handoff rule
When starting a new chat:
1. read `Docs/PROJECT_PASSPORT_v2.md`;
2. read this file;
3. read `Docs/PROJECT_HANDOFF.md`;
4. inspect Git HEAD/status before changing code;
5. continue from `Next action` above;
6. do not reintroduce removed architecture without explicit justification.
