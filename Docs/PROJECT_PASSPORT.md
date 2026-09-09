# TRADER_7_12 PRO — PROJECT PASSPORT

**Дата актуализации:** 09.09.2026  
**Репозиторий:** `Trader_7_12`  
**Ветка:** `main` — единственная рабочая ветка  
**Статус:** production-oriented read-only market-information scanner  
**Версия pipeline:** 2.5.0

## 1. Назначение

Trader_7_12 Pro — read-only информационный сканер текущего рынка. Он анализирует реальные BASE/SPOT-инструменты и показывает объективные рыночные факты: D1-структуру, дневную и текущую относительную силу/слабость к IMOEX2, ликвидность, денежный поток, acceleration и внутридневное положение относительно рынка.

Сканер не выставляет заявки, не управляет позициями, не рассчитывает размер позиции, SL/TP и не исполняет сделки.

## 2. Главный принцип выбора возможности

Ключевая идея проекта — **не абсолютное направление цены инструмента, а его поведение относительно рынка**.

```text
РЫНОК РАСТЁТ
    → ищем СИЛЬНЫЕ относительно рынка инструменты
    → сильнее IMOEX2 = Long-кандидат

РЫНОК ПАДАЕТ
    → ищем СЛАБЫЕ относительно рынка инструменты
    → слабее IMOEX2 = Short-кандидат
```

Примеры:

```text
IMOEX2 -0.8%   акция -0.2%  → RS +0.6 п.п. → СИЛЬНАЯ относительно рынка
IMOEX2 -0.8%   акция -2.5%  → RS -1.7 п.п. → СЛАБАЯ относительно рынка

IMOEX2 +0.8%   акция +1.8%  → RS +1.0 п.п. → СИЛЬНАЯ относительно рынка
IMOEX2 +0.8%   акция +0.1%  → RS -0.7 п.п. → СЛАБАЯ относительно рынка
```

Поэтому красная цена сама по себе не означает Short, а зелёная цена сама по себе не означает Long.

При нейтральном рынке строгий направленный кандидат не создаётся только ради заполнения Radar.

## 3. Цель Radar

Сканер не должен искусственно выдавать ровно 2–3 инструмента. Его рабочая цель — **находить хотя бы 2–3 качественных кандидата, когда рынок предоставляет такое количество объективно подтверждённых возможностей**.

Если подтверждённых кандидатов больше — допускается показать больше в пределах UI capacity. Если их меньше — система не ослабляет критерии искусственно и показывает доступные результаты/диагностику.

## 4. Канонический universe

```text
ALL MOEX TQBR STOCKS
GOLD
OIL
GAS
USDRUB
```

- GOLD: `GLDRUB_TOM`, если доступен как реальный SPOT/base asset в BCS metadata.
- USDRUB: реальный SPOT-инструмент из BCS metadata.
- OIL/GAS: не подменяются фьючерсами; без real base/spot source остаются `UNAVAILABLE`.
- Futures metadata, expiry, mapping и OI — отдельный downstream слой и не заменяют SPOT-анализ.

## 5. Production information pipeline

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
→ MARKET REGIME
→ STRONGER / WEAKER RELATION
→ LONG / SHORT OPPORTUNITY CLASSIFICATION
→ ATTENTION RANKING
```

## 6. D1 classification

`DailyTrendProfileService` работает детерминированно и без сети.

Минимум — 2 завершённых D1 дня, целевой профиль — 3.

### STRONG

- все выбранные свечи зелёные;
- High строго растёт;
- Low строго растёт;
- в каждый сопоставленный день актив сильнее IMOEX2.

### WEAK

- все выбранные свечи красные;
- High строго падает;
- Low строго падает;
- в каждый сопоставленный день актив слабее IMOEX2.

Смешанная структура или непоследовательный D1 RS не квалифицируют инструмент как STRONG/WEAK.

**Важно:** D1 — это контекст и качество состояния инструмента. D1 absolute direction не должен отменять текущую относительную силу/слабость относительно рынка.

## 7. Current-session Relative Strength

```text
RS = asset_current_session_return - benchmark_current_session_return
```

Benchmark:

```text
IMOEX2 → IRUS2 fallback only if IMOEX2 unavailable/unfit
```

Минимальный meaningful current RS:

```text
MIN_MEANINGFUL_RS_PP = 0.10 п.п.
```

## 8. Market regime → direction contract

Текущая торговая ориентация Radar определяется сначала рынком, затем RS инструмента:

```text
benchmark_change >= +0.10 п.п.
    MARKET_REGIME = UP
    RS >= +0.10 п.п. → LONG_CANDIDATE / MARKET_LEADER

benchmark_change <= -0.10 п.п.
    MARKET_REGIME = DOWN
    RS <= -0.10 п.п. → SHORT_CANDIDATE / MARKET_LAGGARD

между порогами
    MARKET_REGIME = NEUTRAL
    строгий Long/Short не создаётся
```

**Запрещено:** требовать `intraday direction == absolute D1 direction` как условие текущей возможности.

Именно относительное поведение против рынка определяет сторону текущей возможности; D1 служит отдельным quality/context gate.

## 9. Liquidity

Percentile не может создать ликвидность.

Production gates:

```text
MIN_MONEY_PER_MINUTE        = 8 000 ₽/min
MIN_RECENT_MONEY_PER_MINUTE = 5 000 ₽/min
```

Оба условия обязательны для strict candidate.

## 10. Flow acceleration

Acceleration сравнивает две полные одинаковые 15-минутные M5-сессии:

```text
recent 15-min pace / previous 15-min pace - 1
```

Нужно по 3 M5 свечи в каждом окне и положительный предыдущий flow. Иначе acceleration = 0.

Attention score:

```text
45% recent ₽×V/min
25% session ₽×V
20% session ₽×V/min
10% acceleration percentile
```

## 11. Radar selection

Strict candidates ранжируются по совокупности:

```text
Relative Strength
+ Attention / flow
+ liquidity
+ D1 quality
```

На растущем рынке Radar может показать несколько лучших сильных инструментов. На падающем рынке — несколько лучших слабых инструментов. Количество не фиксируется как «ровно 2–3».

Целевая практическая выдача — минимум 2–3 качественных кандидата при наличии достаточного рынка; отсутствие необходимого количества не компенсируется снижением объективных критериев.

Если strict qualification недоступна из-за недостатка D1/M5 данных, допускается `ATTENTION_WATCH / WATCH_ONLY`. Watch-only никогда не становится BUY/SELL.

## 12. Broker-style primary radar table

Основная таблица должна читаться как компактная профессиональная market-monitoring таблица без необходимости расшифровывать `RS` по контексту.

```text
# TICKER  ROLE  D1  D1-RS  IDX Δ%  PRICE Δ%  RS vs IDX  ₽/мин  SESSION ₽×V  15m ₽×V  ACCEL  SCORE
```

Определения:

- `IDX Δ%` — текущее изменение выбранного benchmark, фактически `IMOEX2`, либо `IRUS2` при fallback.
- `PRICE Δ%` — текущее изменение конкретного инструмента относительно начала текущей торговой сессии.
- `RS vs IDX` — `PRICE Δ% − IDX Δ%`, в процентных пунктах.
- `₽/мин` — средняя скорость реального денежного оборота с начала текущей торговой сессии.
- `SESSION ₽×V` — накопленный реальный денежный оборот с начала текущей торговой сессии **до момента сканирования**.
- `15m ₽×V` — реальный денежный оборот последних 15 минут.
- `ACCEL` — изменение скорости потока относительно предыдущего полного 15-минутного окна.

Таким образом, текущая таблица одновременно показывает абсолютное движение цены, движение индекса, relative strength и фактический денежный поток. `SESSION ₽×V` не является прогнозом и не является «мгновенным» оборотом: это накопленный оборот на момент конкретного сканирования.

## 13. Coverage

Минимальная production M5 coverage: **80%**.

Ниже 80%:

```text
status = INSUFFICIENT_COVERAGE
```

Coverage — диагностический gate полноты, а не причина скрывать весь рынок.

## 14. Calendar / DSWD

```text
ordinary:
  MORNING  07:00–10:00 MSK
  MAIN     10:00–19:00 MSK
  EVENING  19:00–23:50 MSK

DSWD:
  09:50–19:00 MSK
```

Weekend не считается автоматически закрытым.

## 15. HTTP / data resilience

- один process-wide read-only BCS client;
- bounded concurrency;
- cache/retry для candle requests;
- HTTP/SSL failure не трактуется как отсутствие торгов;
- деградация данных должна отражаться в coverage и diagnostics;
- MOEX ISS Futures OI использует общий `RequestHelper` с нормальной TLS-проверкой и retry-политикой, а не отдельный `urllib`-клиент.

## 16. Futures OI

Futures/OI — отдельный контекстный слой.

Источник OI:

```text
MOEX ISS → /iss/analyticalproducts/futoi/securities
```

MOEX FUTOI использует короткий код инструмента для обычных фьючерсов; полный BCS security/underlying ticker нельзя автоматически считать OI root. Поэтому mapping выполняется в порядке приоритета:

```text
1. явный shortCode / futuresShortCode из BCS metadata
2. каноническое соответствие underlying asset → MOEX short futures code
3. безопасный ticker-root fallback только если он уже совпадает с известным MOEX OI root
```

Для вечных фьючерсов, у которых MOEX использует отдельный код (`APPF`, `AMDF`, `SBERF` и т.п.), root сохраняется отдельно и не смешивается с обычным двухсимвольным контрактом.

OI рассчитывает/показывает:

```text
OI
ΔOI contracts
ΔOI %
OI history
OI-change Z-score
Price + OI regime
Volume confirmation
```

Агрегация client-group строк FUTOI использует обе стороны открытого интереса: при наличии `POS_LONG` и `POS_SHORT` берётся среднее gross-long/gross-short; `POS` используется как fallback. Это не допускает систематического завышения OI одной стороной.

OI не создаёт SPOT-кандидата самостоятельно и не является торговым исполнителем.

### Futures metadata policy

- Для quote-запросов используется `SPBFUT`, если BCS metadata не предоставляет `classCode`.
- `classCode_fallback` диагностируется отдельно и не маскируется под metadata availability.
- Истечение контракта фильтруется только при наличии распознанной даты expiry.
- Если источник metadata не предоставляет expiry, контракт не объявляется истёкшим искусственно; состояние должно оставаться видимым в diagnostics.
- Выбирается front non-expired contract на каждый MOEX OI root; OI остаётся root-level контекстом.
- Diagnostics отдельно показывают `oi_root_mapping`, `oi_available`, `active_roots`, `quote_records` и `expiry_available`.

## 17. Read-only boundary

Программа только показывает рыночную информацию и классификации.

```text
NO ORDER EXECUTION
NO BUY/SELL COMMAND
NO POSITION SIZE
NO SL/TP EXECUTION
NO PORTFOLIO MANAGEMENT
```

## 18. Operational acceptance criteria

Перед объявлением версии готовой проверяются:

1. SPOT universe и benchmark доступны.
2. RS действительно считается относительно IMOEX2/IRUS2.
3. Основная таблица явно показывает `IDX Δ%`, `PRICE Δ%` и `RS vs IDX`.
4. Основная таблица показывает реальный накопленный `SESSION ₽×V` на момент сканирования.
5. На UP market сильнейшие относительно рынка проходят в Long Radar.
6. На DOWN market слабейшие относительно рынка проходят в Short Radar.
7. Абсолютная красная/зелёная свеча не подменяет relative-strength logic.
8. D1 quality не конфликтует с текущей market-regime logic.
9. Liquidity gate остаётся hard gate.
10. M5/flow/acceleration участвуют в ranking и diagnostics.
11. 2–3 качественных кандидата являются целевым минимумом при наличии возможностей, но не искусственным лимитом.
12. При недостатке данных система показывает диагностику и WATCH_ONLY, а не выдумывает сигнал.
13. Futures OI mapping использует корректные MOEX short roots и отдельно учитывает perpetual futures.
14. Futures OI проходит реальную проверку BCS metadata → quotes → MOEX ISS OI.
15. Полный regression suite и macOS build должны быть зелёными.
16. macOS build обязан проходить compile + regression tests до упаковки приложения.
