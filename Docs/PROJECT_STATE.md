# TRADER_7_12 PRO — PROJECT STATE

## CANONICAL CURRENT STATE

Date: 2026-08-17
Branch: `agent/futures-expiry-liquidity`
Repository: `ilshat-71-wq/Trader_7_12`

This file is the single source of truth for the current technical state.

## PRODUCT CONTRACT

Trader_7_12 Pro is a scanner/trading assistant for intraday MOEX futures.

**The user trades ONLY futures.** SPOT is analyzed first to answer:

> Which target SPOT asset has the most meaningful money/activity and structure, and which corresponding FUTURES contract is the practical instrument to watch/trade?

The scanner never places orders. The user makes the final decision on entry, size, risk, SL/TP and execution.

## CORE ARCHITECTURE — SPOT IDEA → FUTURES IMPLEMENTATION

**SPOT creates the trade idea → FUTURES provides the tradable implementation.**

The scanner analyzes the SPOT asset first. The user trades the corresponding futures contract. Pullback/structure is measured on SPOT, never on the futures chart.

The scanner is an analytical filter, not an automatic entry engine. The user personally watches the chart and controls the actual entry point.

## CANONICAL SELECTION RULE

The scanner must NOT start by ranking futures turnover. It starts from target SPOT groups:

1. `MOEX_STOCK` — Moscow Exchange stock / stock metadata;
2. `GAS` — natural gas SPOT;
3. `OIL` — oil SPOT (Brent / crude oil metadata);
4. `USD` — USD/RUB SPOT;
5. `GOLD` — gold SPOT.

Exact SPOT tickers are discovered from BCS metadata and mapping. There is no permanent five-ticker trading universe.

For each target group:

`CURRENT SPOT PRICE × VOLUME`
→ `CURRENT SPOT MONEY LEADER`
→ `SPOT STRUCTURE / STRENGTH`
→ `CORRESPONDING FUTURES`
→ `FUTURES LIQUIDITY / CONFIRMATION`
→ `TOP 2–3 FUTURES`

Current SPOT money/activity and structure have priority over historical futures turnover and radar score.

## SPOT STRUCTURE — CONTEXT, NOT AUTOMATIC ENTRY

The next scanner evolution should recognize the user's preferred early setups on SPOT.

### LONG context

`SPOT impulse up → first pullback down → consolidation / stabilization → strength remains → corresponding FUTURES candidate`

A pullback can be meaningful when it approaches a retracement zone, for example around 50%, or a nearby structural level. The exact entry is deliberately left to the user.

### SHORT context

`SPOT impulse down → first rebound up → consolidation / stabilization → weakness remains → corresponding FUTURES candidate`

The concepts `FIRST_PULLBACK` and `FIRST_REBOUND` are SPOT structure labels. They describe where the target asset is in its movement, not where the futures contract must be bought/sold.

## MONEY DEFINITION

Canonical money metric:

`money_volume = price × volume`

Current SPOT money in the scanner is current-session M5 candle activity; historical completed-day average money remains context for the current/average ratio.

## FUTURES RULE

After a SPOT leader is identified:

- only valid, non-expired futures are eligible;
- contracts with 3 or fewer calendar days to expiry are rejected;
- if multiple expiries map to one SPOT, exactly one liquid futures contract survives;
- futures turnover/confirmation is used to select the practical execution contract and validate the SPOT idea;
- a futures contract with high turnover must not replace a stronger target-SPOT money/structure leader.

## MARKET SESSIONS

All application time is `Europe/Moscow` / MSK. UTC is used only as the technical BCS transport format.

- `06:50–07:00` — `PRE_OPEN`;
- `07:00–10:00` — `MORNING`;
- `10:00–19:00` — `MAIN`;
- `19:00–23:50` — `EVENING`;
- `23:50–06:50` — `CLOSED`.

The UI displays live Moscow date, time with seconds, current session and market-open state. The scanner pipeline is session-aware and attaches session metadata to candidates.

## UI / SCAN FEEDBACK — APPROVED DESIGN

- compact dark neutral professional palette;
- live Moscow session header and clock;
- one compact scan button;
- during scanning the button changes/animates with a pleasant muted green/lime tone;
- the large result area is replaced during scanning by an original animated surreal melting-clock visual inspired by Dali's "The Persistence of Memory";
- when scanning finishes, the animation disappears and the analytical result returns;
- LONG candidate text uses pleasant soft green;
- SHORT candidate text uses pleasant soft red;
- no duplicate scanning status lines;
- no session countdown — the live MSK clock is sufficient;
- results remain analytical/read-only.

The animation is only a scan-state visual and does not change scanner logic.

## IMPLEMENTED BACKEND CHECKPOINT

### `Program/services/futures_morning_radar_service.py`

- keeps valid futures mapped to each SPOT;
- calculates SPOT current-session money once per unique SPOT;
- stores `spot_money_volume`, `spot_average_daily_money`, `spot_money_ratio`;
- sorts radar output with current SPOT money before radar score.

### `Program/services/futures_trade_candidate_service.py`

- canonical target groups: MOEX stock, gas, oil, USD, gold;
- rejects non-target SPOTs;
- selects exactly one current-money leader per target group;
- current SPOT money is primary ranking dimension;
- current/average money ratio is first tie-breaker;
- radar/RS/setup/confirmation and futures liquidity provide quality ordering;
- keeps one most-liquid eligible futures contract per SPOT;
- returns final TOP 2–3 futures candidates.

### `Program/services/session_money_volume_service.py`

- calculates active-session SPOT money/volume metrics;
- supports session-aware evening windows;
- returns zero for closed sessions.

### `Program/services/market_session_service.py`

- centralizes Moscow session boundaries;
- converts timezone-aware UTC values to Moscow time;
- exposes live date/time/session/label/market-open metadata.

### `Program/services/morning_trading_pipeline_service.py`

- session-aware scanner pipeline;
- blocks scanning outside open futures sessions;
- attaches live session metadata to candidates;
- has an evening profile using confirmation and activity;
- remains scanner-only with no orders/risk/position sizing.

## TEST CHECKPOINT

Recently passed regression suites:

- `Program/test_session_money_volume_service.py`
- `Program/test_market_session_service.py`
- `Program/test_morning_trading_pipeline_service.py`
- `Program/test_futures_trade_candidate_service.py`

## IMPORTANT BOUNDARIES

Do not reintroduce automatic orders, automatic entry commands, position sizing, risk management, automatic SL/TP, portfolio management or automatic trade management.

Historical replay is read-only.

## NEXT SCANNER IMPROVEMENT

Implement **SPOT-first structure recognition** without automatic entries:

1. detect a meaningful SPOT impulse;
2. measure the first pullback / first rebound on SPOT;
3. detect consolidation/stabilization near a retracement zone or nearby structural level;
4. preserve SPOT relative strength versus the market benchmark;
5. combine the SPOT setup with current-session money/activity;
6. map the result to the most liquid valid futures contract;
7. present the candidate as an analytical state such as `READY` or `WATCH`;
8. leave the exact entry decision to the user.

Do not measure the first pullback/rebound on the futures chart. Do not turn `FIRST_PULLBACK` / `FIRST_REBOUND` into automatic trade signals. Do not revert to futures-first ranking.

## UI / COMPATIBILITY NOTE

`QPainter` belongs to `PySide6.QtGui`, not `PySide6.QtCore`. This compatibility issue was identified during the latest launch test and is recorded here so it is not reintroduced.

## HANDOFF / VERIFICATION

```bash
cd ~/Documents/Trader_7_12
git pull
python3 -m py_compile \
Program/services/market_session_service.py \
Program/services/session_money_volume_service.py \
Program/services/morning_trading_pipeline_service.py \
Program/services/futures_morning_radar_service.py \
Program/services/futures_trade_candidate_service.py \
Program/ui.py \
Program/main.py \
Program/test_session_money_volume_service.py \
Program/test_market_session_service.py \
Program/test_morning_trading_pipeline_service.py

python3 Program/test_session_money_volume_service.py
python3 Program/test_market_session_service.py
python3 Program/test_morning_trading_pipeline_service.py
python3 Program/test_futures_trade_candidate_service.py

PYTHONPATH="$PWD/Program" python3 Program/main.py
```

## CANONICAL PRINCIPLE TO PRESERVE

**The scanner finds where to look. The user decides where to enter.**

**SPOT determines the idea and structure. FUTURES is what the user trades.**
