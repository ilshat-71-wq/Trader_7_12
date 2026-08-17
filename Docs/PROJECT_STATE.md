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
→ `SPOT H1 STRUCTURE / SUPPORT / RESISTANCE`
→ `SPOT IMPULSE / FIRST PULLBACK OR REBOUND`
→ `SPOT CONSOLIDATION / STABILIZATION`
→ `SPOT STRENGTH / WEAKNESS`
→ `CORRESPONDING FUTURES`
→ `FUTURES LIQUIDITY / CONFIRMATION`
→ `TOP 2–3 FUTURES`

Current SPOT money/activity and structure have priority over historical futures turnover and radar score.

## SPOT STRUCTURE — CURRENT IMPLEMENTATION

The scanner has a dedicated `SpotFirstPullbackService`.

### H1 SPOT STRUCTURE

The user's primary structural timeframe is **H1 on SPOT**. The application therefore treats H1 as the higher-timeframe context and M5 as the session-level formation detector.

For the current SPOT price the service derives:

- nearest H1 support;
- nearest H1 resistance;
- nearest H1 level and its type;
- distance from SPOT price to that level;
- H1 context: `NEAR_H1_SUPPORT`, `NEAR_H1_RESISTANCE` or `BETWEEN_H1_LEVELS`.

A LONG setup receives a controlled quality bonus when the SPOT is near H1 support. A SHORT setup receives a controlled quality bonus when the SPOT is near H1 resistance. This is contextual ranking only — it never creates an automatic entry.

### LONG context

`SPOT H1 structure → impulse up → first pullback down → 35–75% retracement zone → consolidation → strength remains → corresponding FUTURES candidate`

The ideal reference is approximately **50% retracement of the impulse range**, while nearby structural levels are also accepted by the broader 35–75% zone. This is a scanner context filter, not an automatic entry.

### SHORT context

`SPOT H1 structure → impulse down → first rebound up → 35–75% retracement zone → consolidation → weakness remains → corresponding FUTURES candidate`

The detector uses M5 SPOT candles from the **current Moscow trading session** (`MORNING`, `MAIN` or `EVENING`). It does not reuse the morning window after 10:00.

### Setup states

- `WATCH` — first pullback/rebound and stabilization are forming;
- `CONFIRMED` — a later SPOT candle has broken the pullback/rebound confirmation level;
- `WAIT` — no usable setup yet.

The scanner exposes setup quality, impulse size, retracement percentage, consolidation candle count and structural levels. The exact user entry remains outside the application.

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

### `Program/services/spot_first_pullback_service.py`

- SPOT-first structure detector;
- H1 SPOT support/resistance context added as the higher-timeframe structural filter;
- M5 remains the session-level impulse/pullback/rebound detector;
- uses current `MORNING`, `MAIN` or `EVENING` session window;
- detects directional M5 impulse;
- detects first pullback for LONG and first rebound for SHORT;
- accepts 35–75% retracement, with 50% as the quality center;
- detects short consolidation/stabilization;
- exposes `WATCH` / `CONFIRMED` state;
- H1 support/resistance proximity contributes a controlled setup-quality bonus in the matching direction;
- never produces orders or automatic entry commands.

### `Program/services/futures_morning_radar_service.py`

- integrates the SPOT setup detector;
- setup is calculated once per unique SPOT mapping and reused across mapped futures;
- final radar record carries setup phase, quality, impulse, retracement and consolidation metadata;
- ranking gives meaningful weight to SPOT setup quality while preserving current-session SPOT money/activity priority.

### `Program/services/futures_trade_candidate_service.py`

- target groups remain MOEX stock, gas, oil, USD and gold;
- setup quality participates in candidate scoring and final ordering;
- `WATCH` and `CONFIRMED` setup states receive a controlled quality bonus;
- SPOT remains the source of direction/structure;
- FUTURES remains the tradable instrument.

### Existing session/backend services

- `session_money_volume_service.py` — active-session SPOT money/activity;
- `market_session_service.py` — Moscow session boundaries and live clock;
- `morning_trading_pipeline_service.py` — session-aware pipeline;
- `futures_trade_candidate_service.py` — futures confirmation/liquidity selection.

## TEST CHECKPOINT

Regression suites previously passed:

- `Program/test_session_money_volume_service.py`
- `Program/test_market_session_service.py`
- `Program/test_morning_trading_pipeline_service.py`
- `Program/test_futures_trade_candidate_service.py`

Structure tests:

- `Program/test_spot_first_pullback_service.py`
  - LONG pullback near the 50% reference zone;
  - SHORT rebound structure;
  - MAIN-session candle window selection.

H1 structure tests:

- `Program/test_spot_h1_levels_service.py`
  - nearest H1 support context for LONG;
  - nearest H1 resistance context for SHORT.

## IMPORTANT BOUNDARIES

Do not reintroduce automatic orders, automatic entry commands, position sizing, risk management, automatic SL/TP, portfolio management or automatic trade management.

Historical replay is read-only.

Do not measure the first pullback/rebound on the futures chart. Do not turn `FIRST_PULLBACK` / `FIRST_REBOUND` into automatic trade signals. Do not revert to futures-first ranking.

## UI / COMPATIBILITY NOTE

`QPainter` belongs to `PySide6.QtGui`, not `PySide6.QtCore`. This compatibility issue was identified during the latest launch test and is recorded here so it is not reintroduced.

## HANDOFF / VERIFICATION

```bash
cd ~/Documents/Trader_7_12
git pull
python3 -m py_compile \
Program/services/spot_first_pullback_service.py \
Program/services/market_session_service.py \
Program/services/session_money_volume_service.py \
Program/services/morning_trading_pipeline_service.py \
Program/services/futures_morning_radar_service.py \
Program/services/futures_trade_candidate_service.py \
Program/ui.py \
Program/main.py \
Program/test_spot_first_pullback_service.py \
Program/test_spot_h1_levels_service.py \
Program/test_session_money_volume_service.py \
Program/test_market_session_service.py \
Program/test_morning_trading_pipeline_service.py

python3 Program/test_spot_first_pullback_service.py
python3 Program/test_spot_h1_levels_service.py
python3 Program/test_session_money_volume_service.py
python3 Program/test_market_session_service.py
python3 Program/test_morning_trading_pipeline_service.py
python3 Program/test_futures_trade_candidate_service.py

PYTHONPATH="$PWD/Program" python3 Program/main.py
```

## CANONICAL PRINCIPLE TO PRESERVE

**The scanner finds where to look. The user decides where to enter.**

**SPOT determines the idea and structure. FUTURES is what the user trades.**

**H1 is the primary SPOT structural context; M5 is the session formation layer.**
