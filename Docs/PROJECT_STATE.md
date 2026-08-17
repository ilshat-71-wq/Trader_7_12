# TRADER_7_12 PRO — PROJECT STATE

## CANONICAL CURRENT STATE

Date: 2026-08-18
Branch: `agent/scan-speed-optimization`
Repository: `ilshat-71-wq/Trader_7_12`

This file is the single source of truth for the current technical state.

## PRODUCT CONTRACT

Trader_7_12 Pro is a scanner/trading assistant for intraday MOEX futures.

**The user trades ONLY futures.** SPOT is analyzed first to answer which target SPOT asset has the most meaningful money/activity and structure, and which corresponding FUTURES contract is the practical instrument to watch/trade.

The scanner never places orders. The user makes the final decision on entry, size, risk, SL/TP and execution.

## CORE ARCHITECTURE — SPOT IDEA → FUTURES IMPLEMENTATION

**SPOT creates the trade idea → FUTURES provides the tradable implementation.**

The scanner analyzes the SPOT asset first. The user trades the corresponding futures contract. Pullback/structure is measured on SPOT, never on the futures chart.

The scanner is an analytical filter, not an automatic entry engine. The user personally watches the chart and controls the actual entry point.

## CANONICAL FUTURES → SPOT MAPPING

The mapping is explicitly locked to exchange-provided underlying metadata whenever BCS exposes it.

Priority:

1. `baseAssetSecuritySecCode` / equivalent explicit underlying security code;
2. explicit underlying ticker/security object with class code;
3. unique SPOT metadata match only when no explicit underlying metadata exists;
4. ambiguous or unresolved mapping is rejected — the scanner never guesses.

The dynamic futures universe preserves the BCS underlying fields needed by the mapping stage. This keeps the mapping independent of a hand-maintained ticker list.

### Canonical regression

`BMU6` → `BRENT1026` (`Brent Crude Oil 1026`)

Therefore:

**BMU6 / BRENT1026 → SPOT analysis on BRENT1026 → futures BMU6 is the tradable instrument.**

For the application itself, BCS underlying metadata remains the machine-readable mapping source; MOEX documentation is the exchange-level reference used to validate the relationship.

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

The user's primary structural timeframe is **H1 on SPOT**. H1 is the higher-timeframe context and M5 is the session-level formation detector.

For the current SPOT price the service derives nearest H1 support, nearest H1 resistance, nearest H1 level/type, distance to that level, and H1 context (`NEAR_H1_SUPPORT`, `NEAR_H1_RESISTANCE` or `BETWEEN_H1_LEVELS`).

A LONG setup receives a controlled quality bonus when SPOT is near H1 support. A SHORT setup receives a controlled quality bonus when SPOT is near H1 resistance. This is contextual ranking only — it never creates an automatic entry.

### LONG context

`SPOT H1 structure → impulse up → first pullback down → 35–75% retracement zone → consolidation → strength remains → corresponding FUTURES candidate`

The ideal reference is approximately **50% retracement of the impulse range**, while nearby structural levels are also accepted by the broader 35–75% zone. This is a scanner context filter, not an automatic entry.

### SHORT context

`SPOT H1 structure → impulse down → first rebound up → 35–75% retracement zone → consolidation → weakness remains → corresponding FUTURES candidate`

The detector uses M5 SPOT candles from the **current Moscow trading session** (`MORNING`, `MAIN` or `EVENING`).

### Setup states

- `WATCH` — first pullback/rebound and stabilization are forming;
- `CONFIRMED` — a later SPOT candle has broken the pullback/rebound confirmation level;
- `WAIT` — no usable setup yet.

The scanner exposes setup quality, impulse size, retracement percentage, consolidation candle count and structural levels. The exact user entry remains outside the application.

## MONEY DEFINITION

Canonical money metric: `money_volume = price × volume`.

Current SPOT money is current-session M5 candle activity; historical completed-day average money remains context for the current/average ratio.

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

The UI displays live Moscow date, time with seconds and current session. No session countdown is required.

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
- no session countdown;
- results remain analytical/read-only.

## IMPLEMENTED BACKEND CHECKPOINT

### `Program/services/futures_spot_mapping_service.py`

- dynamic Futures → SPOT mapping;
- explicit BCS underlying metadata has priority;
- nested underlying security metadata is supported;
- ambiguous mappings are rejected rather than guessed;
- no permanent manual futures/SPOT ticker universe is required;
- canonical regression is locked: `BMU6 → BRENT1026`.

### `Program/services/spot_first_pullback_service.py`

- SPOT-first structure detector;
- H1 SPOT support/resistance context;
- M5 session impulse/pullback/rebound detector;
- current `MORNING`, `MAIN` or `EVENING` session window;
- 35–75% retracement, with 50% as the quality center;
- consolidation/stabilization;
- `WATCH` / `CONFIRMED` state;
- H1 support/resistance proximity contributes a controlled setup-quality bonus;
- never produces orders or automatic entry commands.

### `Program/services/futures_morning_radar_service.py`

- integrates the SPOT setup detector;
- setup is calculated once per unique SPOT mapping and reused across mapped futures;
- carries setup phase, quality, impulse, retracement and consolidation metadata;
- ranking preserves current-session SPOT money/activity priority.

### `Program/services/futures_trade_candidate_service.py`

- target groups remain MOEX stock, gas, oil, USD and gold;
- setup quality participates in candidate scoring;
- SPOT remains the source of direction/structure;
- FUTURES remains the tradable instrument.

### Existing session/backend services

- `session_money_volume_service.py` — active-session SPOT money/activity;
- `market_session_service.py` — Moscow session boundaries and live clock;
- `morning_trading_pipeline_service.py` — session-aware pipeline;
- `futures_trade_candidate_service.py` — futures confirmation/liquidity selection.

## SCAN PERFORMANCE — CURRENT DEVELOPMENT TARGET

Observed live scans can take roughly four minutes. The next engineering target is **20–30 seconds for a normal scan**, with 15–25 seconds preferred.

Today, without relying on a live BCS session, the repository now contains:

- `Program/services/scan_performance_service.py` — dependency-free stage/total timing utility;
- `Program/test_scan_performance_service.py` — offline regression coverage for the timing utility;
- `Docs/SCAN_PERFORMANCE_PLAN.md` — canonical optimization plan and live-validation checklist.

The optimization plan explicitly targets duplicate historical requests, bounded parallel evaluation of independent SPOT groups, stable-data caching and bounded retry/timeout behavior. Actual network-latency tuning must be validated against BCS during the next open-market run.

## TEST CHECKPOINT

Mapping regression explicitly covers:

- explicit BCS underlying mapping;
- canonical `BMU6 → BRENT1026` mapping;
- nested underlying metadata;
- unique metadata fallback;
- ambiguous mapping rejection;
- explicit metadata taking priority over a name guess.

Existing regression suites cover session, money-volume, morning pipeline, futures candidate, SPOT pullback and H1 levels.

The new offline scan-performance regression covers stage timing, total timing, target classification and invalid target handling.

## IMPORTANT BOUNDARIES

Do not reintroduce automatic orders, automatic entry commands, position sizing, risk management, automatic SL/TP, portfolio management or automatic trade management.

Historical replay is read-only.

Do not measure the first pullback/rebound on the futures chart. Do not turn `FIRST_PULLBACK` / `FIRST_REBOUND` into automatic trade signals. Do not revert to futures-first ranking.

## UI / COMPATIBILITY NOTE

`QPainter` belongs to `PySide6.QtGui`, not `PySide6.QtCore`.

## CANONICAL PRINCIPLE TO PRESERVE

**The scanner finds where to look. The user decides where to enter.**

**SPOT determines the idea and structure. FUTURES is what the user trades.**

**H1 is the primary SPOT structural context; M5 is the session formation layer.**

**Futures → SPOT correspondence comes from explicit exchange/BCS underlying metadata whenever available; never guess an ambiguous mapping.**

**Performance target: a normal scan should complete in 20–30 seconds, without weakening the SPOT-first logic.**
