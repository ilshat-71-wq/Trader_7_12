# Trader_7_12 Pro — Two-Phase Scan Pipeline

## Purpose

Reduce live scan latency toward the 20–30 second target without weakening the SPOT-first trading model.

## Phase 1 — FAST SPOT SCREEN

All mapped SPOT instruments are screened concurrently using only the inexpensive daily radar layer:

- completed daily trend;
- average daily money turnover;
- preliminary radar score;
- direction.

The phase uses bounded concurrency (4 workers).

## Phase 2 — DEEP SPOT ANALYSIS

Only the top 5 SPOT assets from Phase 1 receive the expensive analysis:

- SPOT H1/D context already cached where possible;
- Relative Strength versus the market benchmark;
- SPOT M5 first pullback / first rebound setup;
- setup quality and levels.

Then the existing FUTURES confirmation layer is applied.

## Trading architecture preserved

- SPOT determines the market idea and structure.
- H1 is the primary SPOT structural context.
- M5 is the session formation layer.
- FUTURES is the instrument the user trades.
- BMU6 → BRENT1026 remains the canonical mapping.
- No automatic orders or entry commands are introduced.

## Failure behavior

A failed preliminary request does not stall other SPOTs. A SPOT that cannot provide the required data is not silently converted into a false `no candidates` result.

## Performance expectation

The expensive RS/M5 work is reduced from the complete mapped universe to at most five SPOTs per scan. Together with the existing candle cache and bounded request retry policy, this is the next step toward the 20–30 second live target.
