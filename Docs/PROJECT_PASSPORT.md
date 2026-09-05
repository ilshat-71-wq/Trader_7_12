# TRADER_7_12 PRO — PROJECT PASSPORT

**Дата актуализации:** 05.09.2026  
**Репозиторий:** `ilshat-71-wq/Trader_7_12`  
**Ветка:** `main` — единственная рабочая ветка  
**Статус:** production-oriented read-only market-information scanner  
**Версия pipeline:** 2.3.1

## 1. Назначение

Trader_7_12 Pro — **read-only информационный сканер рынка**. Его задача — в течение текущего торгового дня показывать реальные факты о состоянии доступных BASE/SPOT-инструментов: дневную структуру, относительную силу/слабость к IMOEX2, текущую активность и денежный поток, раннее поведение и реакцию на внутридневные экстремумы индекса.

Сканер не выставляет заявки, не управляет позициями, не рассчитывает размер позиции, SL/TP и **не принимает торговое решение за пользователя**.

## 2. Каноническая D1-классификация

### STRONG — сильная дневная структура

На последних **2–3 завершённых D1 свечах** одновременно:

- все свечи зелёные (`Close > Open`);
- High строго растёт от дня к дню;
- Low строго растёт от дня к дню;
- в каждый сопоставленный день актив сильнее IMOEX2: его дневная доходность выше доходности индекса.

Это объективная классификация состояния инструмента. Она не является торговой рекомендацией.

### WEAK — слабая дневная структура

На последних **2–3 завершённых D1 свечах** одновременно:

- все свечи красные (`Close < Open`);
- High строго падает от дня к дню;
- Low строго падает от дня к дню;
- в каждый сопоставленный день актив слабее IMOEX2: его дневная доходность ниже доходности индекса.

Это объективная классификация состояния инструмента. Она не является торговой рекомендацией.

Смешанная структура или непоследовательный дневной RS не квалифицируют инструмент как STRONG/WEAK. Текущий M5 RS — отдельный текущий факт и не заменяет D1-классификацию.

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

## 4. Production information pipeline

```text
BASE/SPOT UNIVERSE
→ COMPLETED D1 STRUCTURE
→ DAILY RS VS IMOEX2
→ CURRENT SESSION M5
→ EARLY SESSION BEHAVIOUR
→ PRICE / CHANGE / ₽×V / ₽×V-MIN
→ IMOEX2 MIN/MAX REACTION
→ RECENT 15-MIN FLOW
→ ABSOLUTE LIQUIDITY GATE
→ FLOW ACCELERATION
→ CURRENT INTRADAY RS VS IMOEX2
→ MARKET LEADERS / MARKET LAGGARDS
→ ATTENTION RANKING
```

Результат — информационная картина рынка на текущий момент. Программа не говорит пользователю, что покупать, продавать, лонговать, шортить или когда входить.

## 5. Daily Trend Profile contract

`DailyTrendProfileService` is deterministic and network-free. The caller supplies historical D1 candles.

- Current/incomplete trading day is excluded by trading date.
- Daily candles are aligned to Moscow trading date.
- Asset and benchmark are compared by common date, never merely by array position.
- Minimum D1 history: 2 completed days; target: 3.
- Strong/weak structure requires both rising/falling Highs and Lows plus all-green/all-red candles.
- Daily relative confirmation must be consistent across all selected days.
- The service never creates a directional trading signal from incomplete or mixed data.

## 6. Intraday information

Основной внутридневной timeframe: M5. Recent flow window: 15 minutes.

Для каждой доступной бумаги по возможности показываются:

- текущая цена и изменение;
- сессионный ₽×V;
- сессионный ₽×V/min;
- последние 15 минут ₽×V и ₽×V/min;
- ускорение денежного потока;
- текущий RS против IMOEX2;
- ранняя активность;
- реакция на дневной MIN и MAX IMOEX2;
- текущая позиция относительно рынка.

### Раннее торговое окно

Ранние данные используются как отдельный факт текущей сессии. Их вес может зависеть от времени дня, но раннее преимущество не фиксируется навсегда: рынок переоценивается по мере поступления новых данных.

### Экстремумы IMOEX2

Сканер должен сохранять и сравнивать поведение инструментов в ключевых внутридневных точках:

```text
IMOEX2 DAY MIN
IMOEX2 DAY MAX
CURRENT
```

Для каждого инструмента оценивается фактическая реакция в те же временные точки. Это позволяет видеть устойчивость при снижении рынка и слабость при росте рынка без подмены данных прогнозом.

## 7. Flow acceleration — production contract

Acceleration compares two complete, equal 15-minute M5 windows:

```text
recent 15-min pace / previous 15-min pace - 1
```

Valid only when both windows contain 3 M5 candles and previous flow is positive. Otherwise `money_acceleration = 0.0`.

No artificial acceleration cap is applied. Acceleration has only 10% weight in Attention and cannot alone determine market classification.

Attention score:

```text
45% recent ₽×V/min
25% session ₽×V
20% session ₽×V/min
10% acceleration percentile
```

## 8. Absolute liquidity gate

Percentile ranking is not allowed to manufacture liquidity. An instrument must first demonstrate meaningful absolute current activity; only then may it compete on relative ranking.

Production scanner-operational thresholds:

```text
MIN_MONEY_PER_MINUTE        = 8 000 ₽/min
MIN_RECENT_MONEY_PER_MINUTE = 5 000 ₽/min
```

Both conditions are required.

These are operational scanner gates, not MOEX official liquidity classifications. They are time-normalized and work during morning, main, evening and DSWD sessions.

A failed gate produces:

```text
liquidity_status = LOW_LIQUIDITY
liquidity_gate   = false
```

Low-liquidity instruments remain visible in diagnostics but cannot become a market leader/laggard or attention selection.

Coverage is calculated before this gate, so low-liquidity instruments do not masquerade as technical/data failures.

## 9. Benchmark / Relative Strength

Only the real market benchmark is allowed:

```text
IMOEX2 → IRUS2 fallback only if IMOEX2 unavailable/unfit
```

Current-session RS:

```text
RS = asset_current_session_return - benchmark_current_session_return
```

Daily RS:

```text
daily RS = asset_D1_return - IMOEX2_D1_return
```

Meaningful current RS floor:

```text
MIN_MEANINGFUL_RS_PP = 0.10 percentage points
```

Therefore:

```text
RS >= +0.10 pp → meaningful STRONGER
RS <= -0.10 pp → meaningful WEAKER
between → NEUTRAL
```

Shared `RelativeStrengthService` uses the same ±0.10 pp floor.

Benchmark source:

```text
BCS metadata → BCS M5 candles → BCS live quote fallback → unavailable
```

Only real IMOEX2/IRUS2 is allowed. Synthetic benchmark, futures proxy and component-reconstructed index are forbidden.

## 10. Market leader / laggard selection

The scanner may select at most the strongest current market leader and weakest current market laggard from instruments that satisfy all required objective information gates.

```text
MARKET_LEADER:
  completed D1 STRONG structure
  + consistent daily outperformance vs benchmark
  + current-session RS >= +0.10 pp
  + absolute liquidity gate PASS

MARKET_LAGGARD:
  completed D1 WEAK structure
  + consistent daily underperformance vs benchmark
  + current-session RS <= -0.10 pp
  + absolute liquidity gate PASS
```

Это **не торговые рекомендации**. Термины LONG/SHORT, BUY/SELL и «торговый кандидат» не являются частью пользовательской информационной модели.

Ranking is performed after the objective gates:

```text
RS magnitude score = percentile(|current RS|)
Information score = 60% RS magnitude + 40% Attention
```

No result is manufactured to fill a card. If no instrument meets the facts-based criteria, the corresponding block remains empty.

## 11. Output / UI contract

Основной экран должен быть ориентирован на фактическую картину рынка:

```text
ЛИДЕРЫ
АУТСАЙДЕРЫ
ТОП ПО ТЕКУЩЕМУ ИНТЕРЕСУ
```

В строке/карточке инструмента по возможности показываются:

```text
spot_ticker, market_group, price,
change_percent, benchmark, benchmark_change_percent,
relative_strength, relative_strength_status, market_relation,
relative_strength_score, directional_score,
session_money, money_per_minute, recent_money,
recent_money_per_minute, money_acceleration, attention_score,
liquidity_status, liquidity_gate,
daily_structure, daily_structure_state,
daily_relative_direction, daily_relative_mean_pp,
daily_qualified, data_status, pipeline_version
```

При наличии реализованных экстремальных точек также отображаются факты поведения относительно `IMOEX2 MIN`, `IMOEX2 MAX` и `NOW`.

UI не должен использовать формулировки «ЛОНГ-КАНДИДАТ», «ШОРТ-КАНДИДАТ», «ЛОНГОВАТЬ», «ШОРТИТЬ», «ПОКУПАТЬ», «ПРОДАВАТЬ», «ВХОД» как вывод программы.

## 12. Calendar / DSWD

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

Preferred window `09:50–13:00 MSK` is diagnostic/UI information only, never a hard scan gate. Scanner follows the actual open session through close.

## 13. Coverage gate

Minimum production M5 coverage: **80%**.

```text
coverage = analyzed / universe_total
```

Below 80%:

```text
status = INSUFFICIENT_COVERAGE
selected = []
```

Diagnostics expose coverage, skipped count, skip reasons and samples. Partial scan is never presented as a complete market result.

## 14. HTTP resilience

- One process-wide read-only BCS client.
- `MAX_WORKERS = 6`.
- Global request-start throttle: `0.15 s` between requests.
- Reusable `requests.Session` with connection pooling per worker.
- HTTP/SSL failure is not interpreted as no trading.
- 429/SSL degradation must reduce coverage and remain visible in diagnostics.

## 15. Safety boundary

The application is strictly read-only:

```text
NO ORDERS
NO POSITION SIZING
NO SL/TP
NO TRADE EXECUTION
NO AUTOMATIC ENTRY DECISION
NO TRADE RECOMMENDATION
```

The application reports facts and market classifications only. Final decisions remain completely outside the application.
