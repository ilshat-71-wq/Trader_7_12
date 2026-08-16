# TRADER_7_12 PRO — PROJECT HANDOFF

## Use this file to continue the project in a new chat

**Owner / idea author:** Ильшат  
**Technical role:** ChatGPT acts as architect / technical executor  
**Repository:** `ilshat-71-wq/Trader_7_12`  
**Local path:** `~/Documents/Trader_7_12`  
**Branch:** `agent/futures-expiry-liquidity`

### Read first
1. `Docs/PROJECT_PASSPORT_v2.md` — what the product is.
2. `Docs/PROJECT_STATE.md` — exact current technical state.
3. Inspect Git status and HEAD before editing anything.

## Product in one paragraph
Trader_7_12 Pro is a fast morning scanner for intraday MOEX futures. The user trades futures because commissions are lower than on stocks, but analyzes the underlying SPOT asset first. The scanner's job is to evaluate the market, find where money/activity is concentrated, identify the strongest and weakest liquid instruments, consider benchmark-relative strength, trend, levels and setup, confirm the idea with the corresponding futures, and present only 2–3 best instruments. The user then opens charts and decides whether to enter. The application never executes the trade and never calculates position size, risk, SL or TP.

## Core trading concept
- Main trading window: **07:00–10:00 Moscow time**.
- Additional monitoring: **10:00–13:00 Moscow time**.
- Main asset groups: stocks, currencies, gold, oil, gas; other instruments may pass if genuinely liquid and mapped.
- Execution instrument: **futures**.
- Analytical source: **SPOT first**.
- Main market guide: **IMOEX2 / IRUS2 full-return benchmark when genuinely available**.
- Strong asset: rises more than the market when the market rises, or falls less when the market falls.
- Weak asset: falls more than the market when the market falls, or rises poorly when the market rises.
- Money/activity matters: emphasize `price × volume` and the most active liquid instruments of the current day.
- Important context: local levels, previous-day highs/lows and meaningful intraday levels.
- Main setups: BREAKOUT, PULLBACK, REBOUND.
- Output: **TOP 2–3**, large and immediately readable.

## Non-negotiable boundaries
Do NOT add back:
- risk management;
- deposit/risk percentages;
- position sizing / lot calculation;
- automatic SL/TP;
- order execution;
- portfolio management;
- automatic trade management.

Historical replay is **READ ONLY**.

## Architecture
`DYNAMIC FUTURES UNIVERSE`
→ `FUTURES → SPOT MAPPING`
→ `SPOT LIQUIDITY / PRICE×VOLUME`
→ `SPOT DAILY TREND`
→ `RS/WEAKNESS vs IMOEX2 / IRUS2`
→ `LEVELS`
→ `SETUP`
→ `FUTURES CONFIRMATION`
→ `RANKING`
→ `TOP 2–3`
→ `USER DECIDES`

## Current state at handoff
The repository has undergone a scanner-only cleanup. Obsolete legacy scanner/signal/rating/volume/portfolio/risk/manual diagnostic components were removed where no longer needed. Cleanup is dependency-aware; do not delete a service without checking imports and runtime/history dependencies.

Current benchmark rule was changed to prefer `IMOEX2 / IRUS2`. BCS verification on 2026-08-16 found `IMOEX2`, `IMOEX`, and `IMOEXF`; `IRUS2` was not returned. Therefore ordinary `IMOEX` and `IMOEXF` must not silently replace the target full-return benchmark.

Current technical checkpoint is documented in `Docs/PROJECT_STATE.md`.

## Immediate next task
A single known test is stale:
`Program/test_morning_trading_pipeline_service.py`

It expects obsolete `pipeline_version == "0.3"` and currently fails. Review the current pipeline output contract and update the test to validate the current scanner-only behavior instead of restoring obsolete semantics.

Then:
1. compile the affected services;
2. run the pipeline test;
3. run the complete relevant core test set;
4. review the historical replay benchmark behavior;
5. commit and push only after verification.

## Morning live verification
Because Sunday has no trading session, do not invent live results. On the next trading morning, start verification around **07:00 Moscow time** and observe the real BCS data path.

The morning result should be presented in a professional, Russian-language, large-number UI and should answer quickly:
- market direction;
- where the money is;
- strongest candidates;
- weakest candidates;
- `price × volume`;
- SPOT direction/strength;
- levels;
- setup;
- futures confirmation;
- final TOP 2–3.

## Golden rule for future chats
Do not redesign the project from memory. Read the three documents in `Docs/` first, inspect the actual GitHub branch, and continue from the documented `Next action`. If the current code contradicts the passport, investigate the actual code and state before changing architecture.
