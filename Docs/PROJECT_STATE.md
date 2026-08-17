# TRADER_7_12 PRO — PROJECT STATE

## CANONICAL CURRENT STATE — READ THIS FIRST

This file is the single source of truth for the **current technical state** of Trader_7_12 Pro.

- Product architecture and goals: `Docs/PROJECT_PASSPORT_v2.md`
- Current technical state and next action: this file
- Obsolete handoff/cleanup documents are intentionally not used.

## Checkpoint
Date: 2026-08-17
Branch: `agent/futures-expiry-liquidity`
Repository: `ilshat-71-wq/Trader_7_12`

The branch was synchronized with origin before the current architecture work.
Current synchronized base included:
- `0629b51` — `Test BCS futures volume semantics`

The previous local change to `futures_trade_candidate_service.py` was stashed before synchronization and preserved locally under the stash message:
`before-spot-first-money-leader-architecture`.

## Product contract
Trader_7_12 Pro is a scanner/trading assistant for intraday MOEX futures.

**The user trades ONLY futures.** The scanner must therefore answer this practical question:

> Which SPOT asset has the most meaningful money/activity today, and therefore which corresponding FUTURES contract is the best instrument to trade?

The scanner analyzes SPOT first, identifies the day's money leader among the target asset groups, and then selects the corresponding liquid futures contract for execution/confirmation.

The user makes the final decision on entry, position size, risk, SL/TP and execution.

## CORE TRADING PRINCIPLE — SPOT MONEY LEADER → FUTURES

This is now a canonical product rule.

The scanner must NOT start by asking which futures contract is most active.

It must start with the **SPOT market** and determine where the money and trader interest are concentrated today.

Primary target SPOT groups:
1. **Moscow Exchange stock** — the most active / most monetary stock available in the dynamic universe;
2. **Gas**;
3. **Oil**;
4. **Dollar / USD**;
5. **Gold**.

The exact SPOT instruments are discovered dynamically from BCS metadata and current market data. There must be no permanently hard-coded ticker list.

For each target SPOT group the scanner evaluates current-day activity, primarily using:

`PRICE × VOLUME = MONEY VOLUME`

and compares it with normal historical liquidity where available.

The practical selection rule is:

`TARGET SPOT GROUPS`
→ `CURRENT SPOT MONEY / ACTIVITY`
→ `MONEY LEADER OF THE DAY`
→ `CORRESPONDING FUTURES`
→ `FUTURES LIQUIDITY / CONFIRMATION`
→ `TRADE CANDIDATE`

The goal is to find the asset that is interesting to the market **today**, not simply the contract with the largest historical futures volume.

## IMPORTANT DISTINCTION

There are two different concepts:

- **SPOT leader** = where today's underlying market money/activity is concentrated;
- **FUTURES instrument** = the contract the user actually trades.

The first determines the idea. The second is the execution instrument.

Therefore:

`SPOT creates the trade idea → FUTURES provides the tradable implementation and confirmation.`

A futures contract with large volume must not outrank a much more meaningful SPOT money leader merely because its futures turnover is larger.

## TARGET BENCHMARK

Primary benchmark: **IMOEX2 / IRUS2 full-return market benchmark** when genuinely available from BCS.

Current BCS verification:
- `IMOEX2` — found, MOEX index, class `INDX`.
- `IMOEX` — found, MOEX index, class `INDX`.
- `IMOEXF` — found, futures, class `SPBFUT`.
- `IRUS2` — not returned by ticker lookup.

Hard rule:
- prefer `IMOEX2 / IRUS2`;
- never silently substitute ordinary `IMOEX` or `IMOEXF`;
- if the correct benchmark cannot be resolved, RS must be reported as unavailable rather than fabricated.

Historical service uses `RS_TICKERS = ("IMOEX2", "IRUS2")`.

## TARGET ARCHITECTURE

Canonical flow:

`DYNAMIC FUTURES UNIVERSE`
→ `FUTURES → SPOT MAPPING`
→ `TARGET SPOT GROUPS`
→ `SPOT CURRENT PRICE × VOLUME`
→ `SPOT MONEY LEADER`
→ `SPOT DAILY TREND / DIRECTION`
→ `RELATIVE STRENGTH / WEAKNESS`
→ `LOCAL LEVELS / SETUP`
→ `CORRESPONDING FUTURES SELECTION`
→ `FUTURES LIQUIDITY / CONFIRMATION`
→ `QUALITY RANKING`
→ `TOP 2–3`
→ `USER DECIDES`

The architectural priority is now explicitly **SPOT-first money concentration**.

## MONEY LEADER LOGIC

The scanner should identify, for each target SPOT group:

- current-day SPOT money volume;
- average completed-day SPOT money volume;
- current/average money ratio when available;
- current SPOT price movement;
- daily trend;
- relative strength/weakness;
- whether the asset is actually active today.

The most important practical signal is not merely absolute historical turnover. It is:

> **Which target SPOT is attracting meaningful money and attention today?**

Current-day money must therefore have priority over stale historical ranking.

Historical average money remains useful as context and for filtering abnormal/insufficient liquidity, but it must not replace current-day activity.

## TARGET GROUP INTERPRETATION

The initial product target is intentionally narrow and understandable:

- one leading MOEX stock;
- gas;
- oil;
- dollar;
- gold.

This is not a request to hard-code exact tickers. The scanner must resolve the appropriate SPOT instruments dynamically through BCS mapping/metadata.

If multiple futures expiries correspond to the same SPOT, the scanner must choose the **single most appropriate liquid current contract** rather than returning several expiries for the same underlying.

## FUTURES SELECTION RULE

After the SPOT money leader is identified, choose its corresponding futures contract.

The selected futures should be:
- currently valid and not expired;
- uniquely mapped to the SPOT;
- sufficiently liquid;
- preferably the most liquid/current practical expiry;
- confirmed by actual current futures activity when available.

The scanner should not return multiple futures contracts for one SPOT merely because several expiries have trades.

## FUTURES → SPOT MAPPING

Primary service:
`Program/services/futures_spot_mapping_service.py`

Mapping remains dynamic and conservative.

Use confirmed BCS metadata:
- underlying metadata;
- SPOT ticker;
- SPOT class code;
- base asset metadata;
- other confirmed BCS fields.

If the mapping is ambiguous or cannot be resolved uniquely, discard it rather than guessing.

## LIQUIDITY

Key metric:

`money volume = price × volume`

For SPOT, current-day money/activity is the primary selection factor.

For FUTURES, money/volume is primarily used to select the practical tradable contract and confirm that the chosen contract is genuinely active.

Do not fill TOP-3 with illiquid instruments merely to produce three rows.

## DAILY TREND

Daily timeframe remains the main directional context.

Prefer 2–3 days of consistent movement when available.

Working states:
- `UPTREND`;
- `WEAK_UPTREND`;
- `DOWNTREND`;
- `WEAK_DOWNTREND`.

## RELATIVE STRENGTH / WEAKNESS

RS remains a ranking/context factor, but it must be based on a real benchmark.

For LONG candidates prefer stronger SPOT behavior relative to the market.
For SHORT candidates prefer weaker SPOT behavior relative to the market.

If the correct benchmark/data is unavailable:
`RS = UNAVAILABLE`.

Never fabricate neutral/positive/negative RS merely because a field is required downstream.

## SETUPS

Supported setups:
- `BREAKOUT`;
- `PULLBACK`;
- `REBOUND`.

Setup is a secondary decision layer after the SPOT money/activity leader is identified.

## FUTURES CONFIRMATION

The corresponding futures contract confirms that the SPOT idea is actually tradable.

Consider:
- current direction;
- current price movement;
- activity/volume;
- breakout/pullback state;
- quality of movement;
- confirmation timing.

The futures confirmation must not replace SPOT analysis.

## RANKING

Ranking must reflect the new hierarchy:

1. current SPOT money/activity;
2. current SPOT activity relative to normal liquidity;
3. SPOT direction/trend;
4. RS when genuinely available;
5. setup/levels;
6. corresponding futures liquidity;
7. futures confirmation.

Historical average money is context, not the primary daily leader signal.

The score must remain explainable. The purpose is to select the best 2–3 candidates, not create a black box.

## TARGET OUTPUT

The morning output should make the money leader obvious:

```text
TRADER_7_12 PRO — MORNING MONEY LEADERS
TIME: 07:XX MSK

SPOT MONEY LEADERS
1. STOCK: XXXX
   MONEY: ...
   ACTIVITY: ...
   TREND: ...
   RS: ...
   FUTURES: XXXX...
   FUTURES LIQUIDITY: ...
   CONFIRMATION: ...

2. GAS: ...
3. OIL: ...
4. USD: ...
5. GOLD: ...

BEST FUTURES TO TRADE
1. ...
2. ...
3. ...

USER DECIDES THE TRADE.
```

The final TOP 2–3 are the best actionable futures corresponding to the strongest SPOT money/activity leaders and valid setups/confirmation.

## SCANNER-ONLY BOUNDARY

Must NOT reintroduce:
- risk management engine;
- deposit/risk percentage logic;
- position sizing;
- lot calculation;
- automatic SL/TP;
- order execution;
- portfolio management;
- automatic trade management.

Historical replay is READ ONLY and must never place orders.

## CURRENT SERVICES

Core services retained:
- `Program/services/futures_universe_service.py`
- `Program/services/futures_spot_mapping_service.py`
- `Program/services/futures_morning_radar_service.py`
- `Program/services/futures_confirmation_service.py`
- `Program/services/futures_trade_candidate_service.py`
- `Program/services/morning_trading_pipeline_service.py`
- `Program/services/morning_scanner_runner.py`
- `Program/services/morning_radar_service.py`
- `Program/services/morning_money_radar_service.py`
- `Program/services/historical_candidate_ranker_service.py`
- `Program/services/historical_universe_replay_service.py`
- `Program/services/historical_universe_replay_runner.py`
- `Program/services/historical_replay_report.py`

## CURRENT IMPLEMENTATION NOTES

`Program/services/morning_money_radar_service.py` currently provides:
- current/morning money volume;
- average completed-day money volume;
- current/average money ratio;
- money activity score/state.

`Program/services/morning_radar_service.py` currently provides:
- completed daily candles;
- daily trend;
- average daily money via history service.

`Program/services/instrument_morning_radar_service.py` contains legacy/general radar calculations and must not silently override the new SPOT-money-leader hierarchy.

`Program/services/relative_strength_service.py` is an older generic RS calculator whose module documentation still mentions `IMOEXF`. It must be audited before being treated as canonical benchmark logic. Historical benchmark resolution is handled separately.

## LIVE VALIDATION — 2026-08-17

A live scanner run was successfully executed on the morning of 17.08.2026.

BCS authorization succeeded and dynamic futures data was loaded.

Observed runner output:
- `CMU6 / CBOM / LONG` — RADAR 86.67, CONF 95.00, RS 2.85, MONEY VOL 57.39B, SCORE 100.00
- `NVU6 / NVTK / SHORT` — RADAR 86.67, CONF 85.00, RS -0.10, MONEY VOL 17.72B, SCORE 89.91
- `GKU6 / GMKN / SHORT` — RADAR 86.67, CONF 90.00, RS 1.87, MONEY VOL 4.78B, SCORE 79.86

These results prove the live pipeline is operational, but they **do not yet prove that the ranking answers the new product question**. In particular, the observed output ranks by the existing composite futures/candidate pipeline rather than explicitly showing the top SPOT money leaders across stock/gas/oil/USD/gold.

The next implementation work must therefore change the ranking/selection hierarchy, not merely tweak thresholds.

## CURRENT GIT / WORKTREE STATE

Before this canonical update:
- branch was synchronized to `origin/agent/futures-expiry-liquidity` at `0629b51`;
- working tree was clean after stashing the pre-existing local candidate-service modification;
- local stash remains preserved as `before-spot-first-money-leader-architecture`.

## VERIFICATION POLICY

After every code change:
1. inspect the smallest relevant diff;
2. run `python3 -m py_compile` on changed Python files;
3. run the directly relevant unit test(s);
4. run the live scanner when appropriate;
5. commit with a focused message;
6. push to `origin/agent/futures-expiry-liquidity`;
7. verify remote HEAD.

Do not loosen filters merely to force candidates. If a target group has no usable SPOT or futures, report that fact.

## NEXT ACTION

Implement the **SPOT MONEY LEADER → FUTURES** selection hierarchy.

First code task:
- inspect `futures_trade_candidate_service.py`, `futures_morning_radar_service.py`, `morning_trading_pipeline_service.py`, and `morning_scanner_runner.py` together;
- identify where the current ranking starts from futures candidates instead of SPOT money leaders;
- make the smallest architectural change that makes SPOT current-day `PRICE × VOLUME` the primary daily leader signal;
- preserve dynamic BCS mapping and single-futures-per-SPOT behavior;
- preserve scanner-only/read-only boundaries;
- then compile, test, run the live scanner, commit and push.

Do not redesign unrelated services.

## NEW-CHAT TRANSFER RULE

Start every continuation by reading:
1. `Docs/PROJECT_PASSPORT_v2.md`
2. `Docs/PROJECT_STATE.md`

Then inspect:
```bash
git status --short --branch
git log -1 --oneline
```

Continue from `NEXT ACTION` in this file.

Do not rely on chat history when the canonical files contain the required state.
Do not restore removed architecture without explicit justification.
