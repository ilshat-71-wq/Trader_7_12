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

Current SPOT money in the morning pipeline is the actual `07:00–10:00 MSK` M5 candle money volume, using BCS candle `volume × close`.

Historical completed-day average money is context and is used for the current/average ratio. It must not replace current-day activity as the leader signal.

## FUTURES RULE

After a SPOT leader is identified:

- only valid, non-expired futures are eligible;
- contracts with 3 or fewer calendar days to expiry are rejected;
- if multiple expiries map to one SPOT, exactly one liquid futures contract survives;
- futures turnover/confirmation is used to select the practical execution contract and validate the SPOT idea;
- a futures contract with high turnover must not replace a stronger target-SPOT money leader.

## IMPLEMENTED CHANGES — CURRENT CHECKPOINT

### `Program/services/futures_morning_radar_service.py`

- keeps the two nearest valid futures per mapped SPOT;
- calculates SPOT current morning money once per unique SPOT;
- stores:
  - `spot_money_volume`;
  - `spot_average_daily_money`;
  - `spot_money_ratio`;
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

### `Program/test_futures_trade_candidate_service.py`

Regression coverage now verifies:
- target-group filtering;
- one SPOT money leader per group;
- current SPOT money beats radar score;
- one futures contract per SPOT;
- expiry rejection;
- confirmation rejection;
- limit validation.

## IMPORTANT ARCHITECTURAL DISTINCTION

`SPOT creates the trade idea → FUTURES provides the tradable implementation.`

The user trades the futures contract, never the SPOT instrument.

## RELATIVE STRENGTH

RS is a context/ranking factor only. The canonical benchmark work remains `IMOEX2 / IRUS2` when genuinely available. Do not fabricate RS when the correct benchmark is unavailable.

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

The GitHub branch has been updated through the connector because the user's local `~/Documents/Trader_7_12` checkout is not mounted in this session.

Latest remote checkpoint after the architecture changes:
`4bf4b0e` — `Test target SPOT money leader selection`

The previous commits in this implementation are:
- `67282bd` — `Select futures from target SPOT money leaders`
- `bdbf2a8` — `Attach current SPOT money to futures radar`

Required local verification in the user's checkout:

```bash
cd ~/Documents/Trader_7_12
python3 -m py_compile Program/services/futures_morning_radar_service.py Program/services/futures_trade_candidate_service.py Program/test_futures_trade_candidate_service.py
python3 Program/test_futures_trade_candidate_service.py
git status --short --branch
git log -3 --oneline
```

Then run the normal live scanner validation during the morning session and verify that the output shows the target SPOT money leaders first and the corresponding futures second.

## NEXT ACTION

Run local compile/unit verification, then live scanner validation. If the live output is correct, keep this architecture as canonical and continue only with targeted fixes; do not revert to futures-first ranking.
