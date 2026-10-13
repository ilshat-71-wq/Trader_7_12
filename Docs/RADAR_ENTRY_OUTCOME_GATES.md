# Radar entry gates and outcome measurement

Status: implementation on branch audit/radar-entry-outcomes-2026-10-13; merge only after CI and local acceptance.

## Decision chain

1. Move Radar classifies aligned real SPOT moves; it is not an order signal. Non-finite price change, ATR usage, or model score is rejected. Extreme acceleration remains available for audit but is capped at 100 only for tie-breaking.
2. Entry Radar — SPOT requires a directional signal, D1 qualification, confirmed SPOT liquidity gate, finite ATR usage at or below 70%, no explicit EXHAUSTION phase, aligned H1 support/resistance, and the existing setup/M1 confirmation. A confirmed M1 trigger is ENTER only at score >=80; score 65–79.9 is WAIT. Missing/invalid inputs cannot pass.
3. FINAL RADAR — SPOT requires three consecutive scans, established SPOT liquidity gate, score >=80, ATR usage present and <=70%, directional acceleration >=20, START or DEVELOPING phase, and at least two realtime BOOK/TAPE/FLOW components averaging >=55.
4. FINAL RADAR — FUTURES requires three consecutive scans, score >=80, positive real turnover, Money Flow status AVAILABLE, liquidity state ACTIVE/HOT, and no LONG_LIQUIDATION/LIQUIDATE action; realtime confirmation remains required.
5. Missing or non-finite data blocks eligibility. A model score is not empirical win probability.

## Outcome journal

- Stores a confirmed FINAL candidate once per MSK day / instrument / direction in ~/Library/Application Support/Trader_7_12/SignalOutcomeJournal.sqlite3.
- Records observed entry price, instrument class code, direction, score, phase, ATR usage, turnover/pace, and realtime confirmation.
- A background worker queries BCS closed M5 candles and records directional gross close return, MFE and MAE at 5/15/30/60-minute horizons.
- Net return stays null unless TRADER712_ROUND_TRIP_COST_BPS is explicitly set to a verified round-trip cost assumption in basis points. Do not set it by guess.
- This measures outcomes, not simulated execution. It does not invent target/stop levels, submit orders, or claim profitability before sufficient out-of-sample results exist.
- Candidates missing a real price or authoritative class code are stored as INCOMPLETE_DATA and are not evaluated with substitute values.

## Acceptance

Run targeted tests and the full suite from Program. Then verify the macOS build and a live open-session scan. CI passing is necessary but not sufficient for real BCS runtime acceptance.


Validation note: horizon outcomes require a real closed M5 candle at each horizon end; if costs are configured after gross outcomes are stored, the journal fills net results from the stored gross return.


## Aggregate evaluation follow-up — 13.10.2026

- The outcome report now summarizes real closed-M5 outcomes at each horizon using sample size, mean/median gross directional return, and gross win rate.
- Net mean/median/win rate are calculated only from outcomes with an explicit round-trip cost assumption; missing costs remain missing and are never treated as zero.
- The report also breaks results down by observed Move Radar phase and direction. These are observational signal outcomes, not executed trades; repeated signals can remain correlated and sample sizes must be shown alongside metrics.
- This reporting layer does not alter the signal model, trade gates, or order execution.
