# TRADER_7_12 PRO — PROJECT PASSPORT

**Дата актуализации:** 05.09.2026  
**Репозиторий:** `ilshat-71-wq/Trader_7_12`  
**Ветка:** `main` — единственная рабочая ветка  
**Статус:** production-oriented read-only market-attention scanner

## 1. Назначение

Trader_7_12 Pro — read-only сканер внимания рынка. Его задача — в течение текущего торгового дня находить до 2–3 наиболее интересных реальных BASE/SPOT-инструмента, в которых одновременно есть устойчивое дневное направление, заметное отличие от рынка и существенный текущий денежный поток.

Сканер не выставляет заявки, не управляет позициями, не выбирает фьючерсы и не принимает торговое решение за пользователя.

## 2. Каноническая идея направления

### STRONG → LONG candidate

На **последних 2–3 завершённых D1 свечах** одновременно:

- все свечи зелёные (`Close > Open`);
- High строго растёт от дня к дню;
- Low строго растёт от дня к дню;
- в каждый сопоставленный день актив сильнее IMOEX2: его дневная доходность выше доходности индекса.

Это включает оба требуемых случая:

- рынок растёт → актив растёт сильнее;
- рынок падает → актив падает меньше рынка, держится или растёт.

### WEAK → SHORT candidate

На **последних 2–3 завершённых D1 свечах** одновременно:

- все свечи красные (`Close < Open`);
- High строго падает;
- Low строго падает;
- в каждый сопоставленный день актив слабее IMOEX2: его дневная доходность ниже доходности индекса.

Это включает оба случая:

- рынок растёт → актив растёт меньше, стоит или падает;
- рынок падает → актив падает сильнее рынка.

Смешанная структура или непоследовательный дневной RS **не квалифицируют** инструмент. Текущий M5 RS является подтверждением, а не заменой D1-определения сильного/слабого инструмента.

## 3. Канонический universe

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

## 4. Production pipeline

```text
BASE/SPOT UNIVERSE
→ COMPLETED D1 STRUCTURE
→ DAILY RS VS IMOEX2
→ CURRENT SESSION M5
→ PRICE / CHANGE / ₽×V / ₽×V-MIN
→ RECENT 15-MIN FLOW
→ FLOW ACCELERATION
→ INTRADAY RS VS IMOEX2
→ RS MEANINGFULNESS FILTER
→ RS MAGNITUDE + ATTENTION RANKING
→ D1 + DAILY-RS + INTRADAY-RS CONFIRMATION
→ STRONGEST LONG / WEAKEST SHORT
→ MAX 1 WATCH
```

Primary intraday timeframe: M5. Recent flow window: 15 minutes.  
D1 direction window: last 2–3 completed daily candles.

## 5. Daily Trend Profile contract

`DailyTrendProfileService` is deterministic and network-free. The caller supplies historical D1 candles.

- Current/incomplete trading day is excluded by trading date.
- Daily candles are aligned to **Moscow trading date**.
- Asset and benchmark are compared by common date, never merely by array position.
- Minimum D1 history: 2 completed days; target: 3.
- Strong/weak structure requires both rising/falling Highs and Lows plus all-green/all-red candles.
- Daily relative confirmation must be consistent across all selected days.
- The service never creates a directional signal from incomplete or mixed data.

## 6. Flow acceleration — production contract

Acceleration compares **two complete, equal 15-minute M5 windows**:

```text
recent 15-min pace / previous 15-min pace - 1
```

Valid only when both windows contain 3 M5 candles and previous flow is positive. Otherwise `money_acceleration = 0.0`.

No artificial acceleration cap is applied. Acceleration has only 10% weight in Attention and cannot alone determine selection.

Attention score:

```text
45% recent ₽×V/min
25% session ₽×V
20% session ₽×V/min
10% acceleration percentile
```

## 7. Benchmark / Relative Strength

Only the real market benchmark is allowed:

```text
IMOEX2 → IRUS2 fallback only if IMOEX2 unavailable/unfit
```

Current-session RS:

```text
RS = asset_current_session_return - benchmark_current_session_return
```

Daily RS uses same-day D1 returns:

```text
daily RS = asset_D1_return - IMOEX2_D1_return
```

Meaningful current RS floor:

```text
MIN_MEANINGFUL_RS_PP = 0.10 percentage points
```

Therefore:

```text
RS >= +0.10 pp → meaningful STRONG
RS <= -0.10 pp → meaningful WEAK
between → NEUTRAL for directional selection
```

Shared `RelativeStrengthService` uses the same ±0.10 pp floor. No conflicting ±0.20 pp production threshold remains.

Benchmark source:

```text
BCS metadata → BCS M5 candles → BCS live quote fallback → unavailable
```

Only real IMOEX2/IRUS2 is allowed. Synthetic benchmark, futures proxy and component-reconstructed index are forbidden.

## 8. Directional selection

An instrument is eligible for directional output only when **all** required gates agree:

```text
LONG:
  completed D1 STRONG structure
  + consistent daily outperformance vs benchmark
  + current-session RS >= +0.10 pp
  + sufficient current money/activity

SHORT:
  completed D1 WEAK structure
  + consistent daily underperformance vs benchmark
  + current-session RS <= -0.10 pp
  + sufficient current money/activity
```

Ranking:

```text
RS magnitude score = percentile(|current RS|)
Directional score = 60% RS magnitude + 40% Attention
```

Maximum output:

```text
1 LONG_CANDIDATE
1 SHORT_CANDIDATE
1 ATTENTION_WATCH
```

No signal is manufactured to fill a card. If only one qualified side exists, only that side is returned. If none exists, no directional candidate is returned.

## 9. Calendar / DSWD

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

Preferred window `09:50–13:00 MSK` is diagnostic/UI information only, never a hard scan gate. Scanner follows the actual open session through close.

## 10. Coverage gate

Minimum production M5 coverage for directional output: **80%**.

```text
coverage = analyzed / universe_total
```

Below 80%:

```text
status = INSUFFICIENT_COVERAGE
selected = []
```

Diagnostics expose coverage, skipped count, skip reasons and samples. Partial scan is never presented as a complete market result.

D1 availability is separately reported. If the benchmark has insufficient completed D1 history, directional output is forbidden.

## 11. HTTP resilience

- One process-wide read-only BCS client.
- `MAX_WORKERS = 6`.
- Global request-start throttle: `0.15 s` between requests, shared by worker GET/POST.
- Reusable `requests.Session` with connection pooling per worker.
- HTTP/SSL failure is not interpreted as no trading.
- 429/SSL degradation must reduce coverage and remain visible in diagnostics.
- If instability persists, evaluate BCS WebSocket/streaming rather than hiding missing data.

## 12. Output / UI contract

Output includes:

```text
selection_role, spot_ticker, market_group, price,
change_percent, benchmark, benchmark_change_percent,
relative_strength, relative_strength_status, market_relation,
relative_strength_score, directional_score,
session_money, money_per_minute, recent_money,
recent_money_per_minute, money_acceleration, attention_score,
daily_structure, daily_structure_state,
daily_relative_direction, daily_relative_mean_pp,
daily_qualified, data_status, pipeline_version
```

Roles: `LONG_CANDIDATE`, `SHORT_CANDIDATE`, `ATTENTION_WATCH`.

## 13. Runtime safety

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

## 14. Regression contract

Required tests cover:

- 2–3 completed D1 candles;
- all-green rising Highs/Lows → STRONG structure;
- all-red falling Highs/Lows → WEAK structure;
- mixed candles → neutral;
- consistent daily outperformance → LONG confirmation;
- consistent daily underperformance → SHORT confirmation;
- mixed daily RS → no qualification;
- current incomplete D1 excluded;
- daily RS aligned by trading date, not array position;
- D1 confirmation overrides contradictory intraday direction;
- benchmark D1 unavailable → no directional output;
- meaningful RS threshold ±0.10 pp;
- RS magnitude participates in directional ranking;
- IMOEX2 → IRUS2 fallback;
- no benchmark → no directional output;
- recent/current money attention ranking;
- two complete 15-minute acceleration windows;
- incomplete previous window → acceleration 0;
- no futures in universe;
- real GOLD/USDRUB SPOT;
- OIL/GAS not replaced by futures;
- M5 benchmark preferred to quote;
- stale quote rejected;
- nested `boards[].classCode` and IMOEX2 → `INDX`;
- `WEEKENDSESSION=N` exclusion;
- DSWD calendar boundaries including 05.09.2026;
- full-session scanning after 13:00;
- 80% coverage suppression;
- read-only contract.

Before live run:

```bash
python3 -m compileall -q Program
PYTHONPATH=Program python3 -m pytest -q Program
```

## 15. Repository hygiene

Only `main`. No working branches are created.

`Docs/PROJECT_PASSPORT.md` is the **single canonical project MD/checkpoint**. GitHub `main` is canonical source.

```bash
git switch main
git pull --ff-only origin main
```

Old runtime branches/services are not removed by name alone. Cleanup is performed only after import/dependency verification so that working functionality is not destroyed accidentally.

## 16. Current checkpoint — 05.09.2026

```text
Pipeline version:        2.3.0
Runtime:                 BASE/SPOT only
Universe:                ALL TQBR + DSWD eligibility
Macro:                   GOLD / OIL / GAS / USDRUB
Benchmark:               IMOEX2 → IRUS2
Benchmark source:        BCS M5 → BCS quote
Daily benchmark:         completed D1
Timeframes:              D1 direction + M5 flow/confirmation
D1 window:               2–3 completed candles
Recent flow:             15 min
Acceleration:            2 complete comparable 15-min windows
Meaningful RS floor:     ±0.10 percentage points
Directional score:       60% RS magnitude + 40% attention
Current-session scan:    FULL OPEN SESSION → actual close
Preferred window:        09:50–13:00, NOT hard gate
DSWD:                    09:50–19:00 MSK
Coverage gate:           80%
Output:                  LONG + SHORT + max 1 WATCH
Futures analysis:        REMOVED
Order execution:         ABSENT
Read-only:               YES
```

## 17. Validation gate

The canonical source state is the latest `main` commit. Acceptance requires local `compileall` + full `pytest` on the canonical checkout and successful GitHub Actions for the latest commit when CI is available. No arbitrary RS threshold below the documented 0.10 pp floor should be introduced without a separate specification decision.
