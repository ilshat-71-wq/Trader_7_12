# TRADER_7_12 PRO — PROJECT STATE

## CANONICAL CURRENT STATE

Date: 2026-08-17
Branch: `agent/futures-expiry-liquidity`
Repository: `ilshat-71-wq/Trader_7_12`

This file is the single source of truth for the current technical state.

## PRODUCT CONTRACT

Trader_7_12 Pro is a scanner/trading assistant for intraday MOEX futures.

**The user trades ONLY futures.** SPOT is analyzed first to answer:

> Which target SPOT asset has the most meaningful money/activity today, and which corresponding FUTURES contract should be traded/confirmed?

The scanner never places orders. The user makes the final decision on entry, size, risk, SL/TP and execution.

## CANONICAL SELECTION RULE

The scanner must NOT start by ranking futures turnover.

It must start from these target SPOT groups:

1. `MOEX_STOCK` — Moscow Exchange stock `MOEX` / Moscow Exchange metadata;
2. `GAS` — natural gas SPOT;
3. `OIL` — oil SPOT (Brent / crude oil metadata);
4. `USD` — USD/RUB SPOT;
5. `GOLD` — gold SPOT.

Exact SPOT tickers are discovered from BCS metadata and mapping. There is no permanent five-ticker trading universe.

For each target group:

`CURRENT SPOT PRICE × VOLUME`
→ `CURRENT SPOT MONEY LEADER`
→ `CORRESPONDING FUTURES`
→ `FUTURES LIQUIDITY / CONFIRMATION`
→ `TOP 2–3 FUTURES`

Current SPOT money/activity has priority over historical futures turnover and radar score.

## MONEY DEFINITION

Canonical money metric:

`money_volume = price × volume`

Current SPOT money in the scanner is the current-session M5 candle activity; historical completed-day average money remains context for the current/average ratio.

## FUTURES RULE

After a SPOT leader is identified:

- only valid, non-expired futures are eligible;
- contracts with 3 or fewer calendar days to expiry are rejected;
- if multiple expiries map to one SPOT, exactly one liquid futures contract survives;
- futures turnover/confirmation is used to select the practical execution contract and validate the SPOT idea;
- a futures contract with high turnover must not replace a stronger target-SPOT money leader.

## MARKET SESSIONS — CURRENT CHECKPOINT

All application time is `Europe/Moscow` / MSK. UTC is used only as the technical BCS transport format.

`Program/services/market_session_service.py` is now the single session clock:

- `06:50–07:00` — `PRE_OPEN`;
- `07:00–10:00` — `MORNING`;
- `10:00–19:00` — `MAIN`;
- `19:00–23:50` — `EVENING`;
- `23:50–06:50` — `CLOSED`.

The UI now continuously displays:

- Moscow date;
- Moscow time with seconds;
- current session;
- whether the market is open;
- session-specific subtitle.

The scanner pipeline is session-aware: it refuses to run in `PRE_OPEN`/`CLOSED` and attaches `market_session`, `market_session_label`, `market_date`, `market_time` and `market_timezone` to candidates.

The evening/main scan is therefore no longer presented as a generic "morning" result. The next backend refinement is to make the SPOT setup/money window itself session-specific rather than only session-labelled.

## UI / SCAN FEEDBACK

`Program/ui.py` now provides:

- live session header;
- dynamic session subtitle;
- background scan in a Qt worker thread;
- animated purple scan-status line while BCS analysis is running;
- explicit completion/error state;
- current-session timestamp in the result;
- fallback display for a zero `entry_trigger` using the relevant previous level;
- read-only scanner presentation with no risk sizing or order execution.

## IMPLEMENTED CHANGES — CURRENT CHECKPOINT

### `Program/services/futures_morning_radar_service.py`

- keeps the two nearest valid futures per mapped SPOT;
- calculates SPOT current-session money once per unique SPOT;
- stores `spot_money_volume`, `spot_average_daily_money`, `spot_money_ratio`;
- sorts radar output with current SPOT money before radar score.

### `Program/services/futures_trade_candidate_service.py`

- canonical target groups: MOEX stock, gas, oil, USD, gold;
- rejects non-target SPOTs;
- selects exactly one current-money leader per target group;
- current SPOT money is the primary ranking dimension;
- current/average money ratio is the first tie-breaker;
- then radar/RS/setup/confirmation and futures liquidity provide quality ordering;
- keeps one most-liquid eligible futures contract per SPOT;
- returns the final requested TOP 2–3 futures candidates.

### `Program/services/market_session_service.py`

- centralizes Moscow session boundaries;
- converts timezone-aware UTC values to Moscow time;
- exposes live `date`, `time`, `session`, `label`, `market_open` and session window metadata.

### `Program/services/morning_trading_pipeline_service.py`

- version `0.5`;
- blocks scanning outside open futures sessions;
- attaches live session metadata to every candidate;
- keeps scanner-only architecture with no orders/risk/position sizing.

### Tests

- `Program/test_futures_trade_candidate_service.py` — target-group/liquidity/expiry/confirmation regression coverage;
- `Program/test_morning_trading_pipeline_service.py` — session metadata and scanner-only regression coverage;
- `Program/test_market_session_service.py` — exact session boundary and UTC→MSK conversion tests.

## IMPORTANT ARCHITECTURAL DISTINCTION

`SPOT creates the trade idea → FUTURES provides the tradable implementation.`

The user trades the futures contract, never the SPOT instrument.

## RELATIVE STRENGTH

RS is a context/ranking factor only. The canonical benchmark is `IMOEX2 / IRUS2` when genuinely available. Do not fabricate RS when the correct benchmark is unavailable.

## BOUNDARIES

Do not reintroduce:
- automatic orders;
- position sizing;
- risk management engine;
- automatic SL/TP;
- portfolio management;
- automatic trade management.

Historical replay is read-only.

## VERIFICATION / HANDOFF

The GitHub branch is synchronized with the user's local branch `agent/futures-expiry-liquidity` after the user's successful push.

Recent session/UI commits on the same branch:
- `46f3783a` — improve Moscow market session metadata;
- `3751db15` — make radar UI session-aware and show animated scan state;
- `0a486bbb` — make scanner pipeline session-aware;
- `584177b3` — test session-aware scanner metadata;
- `66b9f377` — add market-session boundary tests.

Required local verification in the user's checkout:

```bash
cd ~/Documents/Trader_7_12
python3 -m py_compile Program/services/market_session_service.py Program/services/morning_trading_pipeline_service.py Program/services/futures_morning_radar_service.py Program/services/futures_trade_candidate_service.py Program/ui.py Program/main.py Program/test_market_session_service.py Program/test_morning_trading_pipeline_service.py
python3 Program/test_market_session_service.py
python3 Program/test_morning_trading_pipeline_service.py
python3 Program/test_futures_trade_candidate_service.py
git status -sb
git log -6 --oneline
```

Then run the live scanner. The UI must show the actual Moscow session and time. During a scan the purple status line must visibly animate. A scan during `MAIN` or `EVENING` must not be labelled as a morning scan.

## NEXT ACTION

After local verification, the next scanner improvement is **true session-specific market analysis**:

1. use `07:00–10:00` data for `MORNING`;
2. use `10:00–19:00` data for `MAIN`;
3. use `19:00–23:50` data for `EVENING`;
4. keep daily trend/RS based only on completed daily candles;
5. calculate current-session SPOT money and setup from the active session window;
6. keep futures confirmation aligned with the same active session;
7. compare session-aware replay results before changing ranking weights.

Do not revert to futures-first ranking and do not reintroduce risk/order layers.