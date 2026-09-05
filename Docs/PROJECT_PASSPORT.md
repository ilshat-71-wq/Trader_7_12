# TRADER_7_12 PRO — PROJECT PASSPORT

**Дата актуализации:** 05.09.2026  
**Репозиторий:** `ilshat-71-wq/Trader_7_12`  
**Ветка:** `main` — единственная рабочая ветка  
**Статус:** production-oriented read-only market-attention scanner

## 1. Назначение

Trader_7_12 Pro — read-only сканер внимания рынка. Он показывает наиболее активные реальные BASE/SPOT-инструменты и их силу/слабость относительно реального рыночного benchmark.

Сканер не выставляет заявки, не управляет позициями, не выбирает фьючерсы и не принимает торговое решение за пользователя.

## 2. Канонический universe

```text
ALL MOEX TQBR STOCKS
GOLD
OIL
GAS
USDRUB
```

- GOLD: `GLDRUB_TOM`, если доступен в BCS SPOT metadata.
- USDRUB: реальный spot-инструмент из BCS metadata.
- OIL/GAS: не заменяются фьючерсами; без real base/spot source → `UNAVAILABLE`.
- Futures metadata, expiry, mapping и ranking в runtime отсутствуют.
- На ДСВД stock universe фильтруется по MOEX `WEEKENDSESSION`, если поле доступно; `WEEKENDSESSION=N` исключается.
- Если `WEEKENDSESSION` не отдан BCS, бумага не удаляется молча; фактическая M5-доступность может использоваться как дополнительная проверка.

## 3. Pipeline

```text
BASE/SPOT UNIVERSE
→ CURRENT SESSION M5
→ PRICE / CHANGE / ₽×V / ₽×V-MIN
→ RECENT 15-MIN FLOW
→ FLOW ACCELERATION
→ IMOEX2 / IRUS2 BENCHMARK
→ INTRADAY RELATIVE STRENGTH
→ ATTENTION SCORE
→ STRONGEST LONG / WEAKEST SHORT
→ COMPACT WATCHLIST
```

Primary timeframe: M5. Recent flow window: 15 minutes.

## 4. Flow acceleration — production contract

Acceleration compares **two complete, equal 15-minute M5 windows**:

```text
recent 15-min pace / previous 15-min pace - 1
```

Calculation is valid only when both windows contain 3 M5 candles and previous flow is positive. Otherwise `money_acceleration = 0.0`.

No artificial acceleration cap is applied: a large value is valid when caused by real comparable flow rates. Acceleration has only 10% weight in attention and cannot alone determine selection.

Attention score:

```text
45% recent ₽×V/min
25% session ₽×V
20% session ₽×V/min
10% acceleration percentile
```

`attention_score` is relative market attention, not probability of profit.

## 5. Benchmark / Relative Strength

Priority:

```text
IMOEX2 → IRUS2 fallback only if IMOEX2 unavailable/unfit
```

```text
RS = asset_current_session_return - benchmark_current_session_return
```

Benchmark source:

```text
BCS metadata → BCS M5 candles → BCS live quote fallback → unavailable
```

Only real IMOEX2/IRUS2 is allowed. Synthetic benchmark, futures proxy and component-reconstructed index are forbidden.

Quote fallback requires open, current price and fresh timestamp. If benchmark is unavailable, directional LONG/SHORT selection is forbidden.

BCS `classCode` is supported both at top level and inside `boards[].classCode`; IMOEX2 resolves to real `INDX`.

## 6. Directional selection

```text
LONG  = RS > 0 + high current activity + highest attention among strong
SHORT = RS < 0 + high current activity + highest attention among weak
```

A strong asset can be LONG on a falling market; a weak asset can be SHORT on a rising market.

No arbitrary RS threshold is currently introduced. Changing the sign-based RS methodology is a separate specification decision, not a bugfix.

## 7. Calendar / DSWD

Weekend is not automatically CLOSED.

```text
ordinary:
  MORNING  07:00–10:00 MSK
  MAIN     10:00–19:00 MSK
  EVENING  19:00–23:50 MSK

DSWD:
  09:50–19:00 MSK
```

**05.09.2026 is a real DSWD trading day, 09:50–19:00 MSK.**

No DSWD in 2026: 12–13 Sep, 24–25 Oct, 28–29 Nov. DSWD is scheduled for 05–06 Dec.

User preferred window `09:50–13:00 MSK` is **diagnostic/UI information only, never a hard scan gate**. Scanner follows the actual open session from `session_start` to actual close. Before session / after close → explicit `MARKET_CLOSED`.

## 8. Coverage gate

Minimum production coverage for directional output: **80%**.

```text
coverage = analyzed / universe_total
```

Below 80%:

```text
status = INSUFFICIENT_COVERAGE
selected = []
```

Diagnostics expose coverage, skipped count, skip reasons and sample tickers. Partial scan is never treated as a complete market result.

## 9. HTTP resilience

- One process-wide read-only BCS client.
- `MAX_WORKERS = 6`.
- Global request-start throttle: `0.15 s` between requests, shared by worker GET/POST.
- Reusable `requests.Session` with connection pooling per worker.
- HTTP/SSL failure is not interpreted as no trading.
- 429/SSL degradation must reduce coverage and remain visible in diagnostics.
- If instability persists, evaluate BCS WebSocket/streaming rather than hiding missing data.

## 10. Output / UI

Output contract includes:

```text
selection_role, spot_ticker, market_group, price,
change_percent, benchmark, benchmark_change_percent,
relative_strength, relative_strength_status, market_relation,
session_money, money_per_minute, recent_money,
recent_money_per_minute, money_acceleration, attention_score,
data_status, pipeline_version
```

Roles: `LONG_CANDIDATE`, `SHORT_CANDIDATE`, `ATTENTION_WATCH`.

UI contract: 1 LONG + 1 SHORT + maximum 1 WATCH; diagnostics secondary.

## 11. Runtime safety

Forbidden:

```text
order execution
position sizing
SL/TP automation
futures selection / confirmation
synthetic SPOT
synthetic RS
FUTURES_DIRECT fallback
synthetic benchmark
```

Refresh token is local only:

```text
~/.config/Trader_7_12/bcs_refresh_token
chmod 600
```

Secrets are not stored in Git.

## 12. Regression contract

Required tests cover:

- strong/weak assets against rising/falling benchmark;
- IMOEX2 → IRUS2 fallback;
- no benchmark → no directional output;
- benchmark + RS on directional candidates;
- recent/current money attention ranking;
- two complete 15-minute acceleration windows;
- incomplete previous window → acceleration 0;
- extreme acceleration does not break 0–100 attention ranking;
- no futures in universe;
- real GOLD/USDRUB SPOT;
- OIL/GAS not replaced by futures;
- M5 benchmark preferred to quote;
- stale quote rejected;
- nested `boards[].classCode` and IMOEX2 → `INDX`;
- `WEEKENDSESSION=N` exclusion;
- DSWD calendar boundaries including 05.09.2026;
- full-session scanning after 13:00;
- 80% coverage suppression and partial-scan diagnostics;
- read-only contract.

Before live run:

```bash
python3 -m compileall -q Program
PYTHONPATH=Program python3 -m pytest -q Program
```

## 13. Repository hygiene

Only `main`. No working branches are created.

`Docs/PROJECT_PASSPORT.md` is the **single canonical project MD/checkpoint**. GitHub `main` is canonical source.

```bash
git switch main
git pull --ff-only origin main
```

Current GitHub audit: only `main` exists; no open PRs. Existing regression, build and workflow files are retained because they are technically relevant.

## 14. Current checkpoint — 05.09.2026

```text
Pipeline version:        2.2.2
Runtime:                 BASE/SPOT only
Universe:                ALL TQBR + DSWD eligibility
Macro:                   GOLD / OIL / GAS / USDRUB
Benchmark:               IMOEX2 → IRUS2
Benchmark source:        BCS M5 → BCS quote
IMOEX2 class code:       INDX
Timeframe:               M5
Recent flow:             15 min
Acceleration:            2 complete comparable 15-min windows
Current-session scan:    FULL OPEN SESSION → actual close
Preferred window:        09:50–13:00, NOT hard gate
DSWD:                    09:50–19:00 MSK
Coverage gate:           80%
Output:                  LONG + SHORT + max 1 WATCH
Futures analysis:        REMOVED
Order execution:         ABSENT
Read-only:               YES
```

## 15. Live validation history — 05.09.2026

- DSWD 05.09.2026 verified as a real MOEX trading session.
- Live BCS `IMOEX2 / INDX` M5 data observed during DSWD.
- Real BASE/SPOT LONG/SHORT candidates observed with benchmark-relative strength.
- Initial broad DSWD run `79/263` was rejected as incomplete after burst 429.
- Request-start throttling reduced burst-429 pattern; transient SSL failures remained a resilience concern.
- Connection pooling and `WEEKENDSESSION` filtering are now part of production architecture.
- Erroneous 13:00 hard gate removed; scanner now follows full open session.
- Acceleration corrected to comparable complete 15-minute windows. Live sample `MAGN +1454.1%` is not automatically erroneous because it is a ratio of real comparable flow rates and has 10% attention weight.
- Regression test `test_flow_acceleration_requires_two_complete_15_minute_windows` verifies incomplete previous windows produce zero acceleration.

## 16. Validation gate

The canonical source state is the latest `main` commit. The final acceptance gate is: local `compileall` + full `pytest` on the canonical checkout, followed by successful GitHub Actions for the latest commit. No RS-threshold methodology change is introduced without a separate specification decision.
