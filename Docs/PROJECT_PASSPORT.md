# TRADER_7_12 PRO — PROJECT PASSPORT

**Дата актуализации:** 26.08.2026  
**Репозиторий:** `ilshat-71-wq/Trader_7_12`  
**Главная и единственная рабочая ветка:** `main`

---

## 1. ГЛАВНАЯ ЦЕЛЬ

Trader_7_12 Pro — аналитический scanner/assistant для самостоятельной интрадей-торговли фьючерсами Московской биржи.

Сканер **не сканирует фьючерсный рынок как источник идеи**. Он ищет 2–3 наиболее интересных **базовых актива (SPOT)**, в которых сегодня есть деньги, активность, движение и понятная сила/слабость.

Канонический принцип:

> **Сканер находит ГДЕ смотреть. Пользователь самостоятельно выбирает фьючерс, график и точку входа.**

Приложение не исполняет сделки и не заменяет решение пользователя.

---

## 2. КАНОНИЧЕСКАЯ АРХИТЕКТУРА

```text
SPOT
  ↓
SPOT MONEY / ACTIVITY
  ↓
SPOT DIRECTION / DAILY TREND
  ↓
SPOT RELATIVE STRENGTH / WEAKNESS vs IMOEX2 / IRUS2
  ↓
SPOT H1 STRUCTURE + M5 SETUP
  ↓
SETUP STATE / TRIGGER / READINESS
  ↓
TOP 2–3 SPOT OPPORTUNITY WATCHLIST
  ↓
USER SELECTS THE FUTURES CONTRACT
```

**Ключевое правило:** данные, ликвидность, движение и подтверждение фьючерса **не участвуют** в eligibility, direction, RS, setup или ranking базового актива.

Фьючерсный mapping может существовать только как справочная связь `BASE ASSET → соответствующий контракт`, чтобы пользователь понимал, чем потенциально торговать.

---

## 3. ЧТО ИЩЕМ

Кандидат должен иметь как можно больше следующих признаков:

1. `price × volume` / money;
2. необычную текущую активность относительно собственной нормы;
3. достаточную SPOT ликвидность;
4. полезную волатильность и потенциал;
5. направленность и дневный контекст;
6. относительную силу или слабость относительно рынка;
7. качественную SPOT-структуру;
8. pullback/rebound или breakout setup;
9. возможность продолжения движения.

TOP-2/3 — это **watchlist возможностей**, а не список готовых входов. WAIT/WATCH могут оставаться в TOP, если базовый актив проходит обязательные SPOT eligibility-проверки.

Если качественных кандидатов меньше трёх, TOP не заполняется искусственно.

---

## 4. UNIVERSE

Общий universe:

`IMOEX stocks + OIL + GOLD + GAS + USDRUB`

Состав IMOEX загружается динамически через MOEX ISS.

Отдельные market drivers OIL/GOLD/GAS/USDRUB анализируются как самостоятельные SPOT-активы и конкурируют с IMOEX-акциями за общий TOP 2–3.

Нельзя заранее резервировать места по группам.

---

## 5. SPOT MONEY / ACTIVITY

Каноническая метрика:

`money_volume = price × volume`

Учитываются:

- текущий SPOT money volume;
- средний оборот завершённых торговых дней;
- текущий session money volume;
- money volume в единицу времени;
- текущая активность относительно ожидаемой активности.

Ключевой показатель:

`activity_ratio = current_session_money / expected_money_to_now`

Абсолютный оборот не должен автоматически делать актив лидером: важна аномальность текущей активности относительно собственной нормы.

---

## 6. MARKET BENCHMARK — IMOEX2 / IRUS2

Главный benchmark российского рынка — `IMOEX2 / IRUS2`.

Он используется для market context и Relative Strength.

### Сильный SPOT-актив

Для LONG предпочтителен актив, который:

- растёт быстрее рынка при росте рынка;
- падает медленнее рынка при снижении рынка;
- сохраняет относительное превосходство после отката.

### Слабый SPOT-актив

Для SHORT предпочтителен актив, который:

- падает быстрее рынка при снижении рынка;
- растёт хуже рынка при росте рынка;
- сохраняет относительную слабость после отскока.

Формула:

`relative_strength = instrument_return - benchmark_return`

Положительный RS означает превосходство SPOT над benchmark; отрицательный — относительную слабость.

Канонические сигналы:

- `STRONGER` — RS ≥ 0.20 п.п.;
- `WEAKER` — RS ≤ -0.20 п.п.;
- `NEUTRAL` — промежуточная зона;
- `RS_UNAVAILABLE` — обязательные данные benchmark отсутствуют.

Фиктивный RS запрещён.

---

## 7. DIRECTION / DAILY TREND

Daily timeframe — базовый контекст.

Предпочтительны 2–3 последовательных дня движения в одном направлении, но это не абсолютный запрет.

Для ranking RS должен согласовываться с направлением:

- `LONG + STRONGER` — плюс;
- `SHORT + WEAKER` — плюс;
- `LONG + WEAKER` — штраф;
- `SHORT + STRONGER` — штраф.

Direction является SPOT-свойством и может определяться в любой момент, когда доступны необходимые SPOT/daily данные; фьючерс не является источником direction.

---

## 8. SPOT STRUCTURE / SETUP / READINESS

Основной контекст — H1 SPOT.

Формирование текущего сценария — M5 SPOT.

LONG:

`H1 up → impulse → first pullback → stabilization → continuation`

SHORT:

`H1 down → impulse → first rebound → stabilization → continuation`

Рабочая зона retracement ориентировочно 35–75% импульса, с ориентиром около 50%.

Состояния:

- `WAIT` — идея интересна, но setup ещё не сформирован;
- `WATCH` — setup развивается и требует наблюдения;
- `READY` — setup сформирован и имеет фактический trigger/readiness;
- `CONFIRMED` — подтверждение сценария по каноническим SPOT-условиям.

`READY/CONFIRMED` не являются разрешением на автоматическую сделку. Они описывают степень готовности SPOT-сценария.

**Setup quality и opportunity score — разные измерения.** Высокий opportunity score не означает готовый вход.

---

## 9. RANKING

Итоговый вопрос:

> **Где сегодня одновременно есть деньги, активность, движение, сила/слабость и качественный SPOT context?**

Итоговый `opportunity_score` формируется session-aware pipeline из существующего SPOT `candidate_score`, текущей активности и направленного движения.

Setup quality выводится отдельно и не используется как обязательный финальный gate TOP-2/3.

Приоритеты остаются:

1. current SPOT money/activity;
2. SPOT strength/weakness vs benchmark;
3. SPOT liquidity/volume;
4. volatility/potential;
5. direction/daily trend;
6. SPOT setup quality;
7. data quality/freshness.

**Фьючерсные trades, futures price movement, futures turnover и futures confirmation не входят в ranking.**

---

## 10. FUTURES MAPPING

Mapping нужен только для справочной связи выбранного базового актива с торговым инструментом пользователя.

Каноническое правило:

> **Сначала выбирается BASE ASSET. Только после этого пользователь самостоятельно выбирает подходящий фьючерсный контракт.**

Фьючерсный mapping не должен менять:

- направление;
- RS;
- score;
- setup;
- readiness;
- TOP ranking.

Futures confirmation **не является обязательным фильтром** и не должна превращаться в gate SPOT-сценария.

---

## 11. ДВУХФАЗНЫЙ PIPELINE

### FAST SCREEN

Для universe используются дешёвые SPOT-признаки:

- daily trend;
- average money;
- current SPOT change/momentum;
- preliminary activity;
- preliminary radar score.

### DEEP ANALYSIS

Только лучшие кандидаты получают:

- SPOT RS;
- H1 structure;
- M5 pullback/rebound;
- volatility/potential;
- setup quality;
- trigger/readiness;
- detailed session money/activity.

После этого группы объединяются и выбирается TOP 2–3 watchlist.

---

## 12. ВАЛИДИРОВАННЫЙ CHECKPOINT

- Production и historical ranking используют одинаковый directional RS tie-break: для LONG выше положительный RS, для SHORT более отрицательный RS.
- Futures turnover, futures price и futures confirmation остаются полностью вне SPOT score/ranking.
- Production candidate не проходит без доступного положительного/отрицательного RS в соответствии с направлением.
- `moex_event_risk` остаётся жёстким SPOT eligibility gate даже при сильных остальных сигналах.
- Historical replay остаётся `READ ONLY / NO ORDERS`.
- Регрессионный набор SPOT-first покрывает независимость от futures, readiness, production/historical directional RS tie-break, отсутствие RS и event-risk gate.
- Канонический документ проекта — только `Docs/PROJECT_PASSPORT.md`.
- Рабочая ветка проекта — только `main`.

---

## 13. ПРОДАКШЕННЫЙ SPOT-RANKING CHECKPOINT

- `FuturesMorningRadarService` теперь пропускает production radar через канонический `FuturesTradeCandidateService.build_candidate()` до ranking и до futures mapping.
- Production `candidate_score` является первичным ключом ranking; `setup_quality_score` больше не может самостоятельно поднять слабый SPOT-кандидат выше более сильного opportunity.
- Production tie-break по RS направлен относительно сделки: LONG → больший RS, SHORT → более отрицательный RS.
- Futures mapping выполняется только после прохождения SPOT eligibility и наличия рабочего SPOT trigger/readiness.
- Futures confirmation, turnover, price, spread и expiry не участвуют в SPOT eligibility или score.
- Добавлены production regression tests для candidate-score ranking и запрета futures attachment до SPOT readiness.

---

## 14. FULL CI / AUDIT CHECKPOINT

**Дата:** 26.08.2026  
**Коммит:** `39ba4b328e449889675242a03558e14383e6ee37`  
**GitHub Actions:** `SPOT-first validation` — **SUCCESS**

Проверено полным CI:

- Python 3.11;
- `compileall` для `Program/services` и `Program/tests` — SUCCESS;
- полный `Program/tests` — **14 passed**;
- исправлена только инфраструктурная причина предыдущего падения CI: runner не устанавливал runtime-зависимость `requests`;
- в production/historical SPOT ranking логике дополнительных функциональных изменений в рамках этого аудита не потребовалось;
- `FuturesTradeCandidateService` использует только SPOT evidence для eligibility/score;
- `FuturesMorningRadarService` выполняет SPOT eligibility до futures mapping;
- historical ranker использует directional RS tie-break и не использует futures metrics;
- единственный канонический паспорт проекта сохранён: `Docs/PROJECT_PASSPORT.md`;
- рабочая ветка остаётся только `main`.

**Аудиторский вывод:** на текущем checkpoint SPOT-first regression suite проходит полностью. Последний CI failure был dependency/configuration failure (`requests` отсутствовал в runner), а не функциональный regression проекта. После добавления `requests` в CI полный набор из 14 тестов прошёл успешно.

---

## 15. SPOT READINESS / FUTURES MAPPING BOUNDARY CHECKPOINT

**Дата:** 26.08.2026  
**Коммит с regression coverage:** `33c829789aad0453c5bfe2d8eebd8a0113b8a0b0`  
**GitHub Actions:** `SPOT-first validation` run #20 — **SUCCESS**

Добавлена production-level regression coverage границы `SPOT → FUTURES MAPPING`:

- `READY` SPOT-кандидат с валидным trigger/readiness действительно может получить справочный futures mapping;
- `WAIT` SPOT-кандидат не получает futures ticker даже при наличии готового mapping в исходных данных;
- `moex_event_risk=True` блокирует candidate до futures mapping даже при сильных SPOT money/RS/setup сигналах;
- тест проверяет не только конечный результат, но и сам факт вызова mapping только после SPOT readiness;
- futures mapping остаётся reference-only и не меняет candidate eligibility или ranking.

Полный CI после исправления тестового ожидания:

- Python 3.11 — SUCCESS;
- `compileall` — SUCCESS;
- полный `Program/tests` — **16 passed**;
- `SPOT-first validation` — **SUCCESS**.

**Аудиторский вывод:** production pipeline теперь имеет regression coverage не только для запрета преждевременного futures attachment, но и для положительного пути `eligible SPOT + READY + trigger → post-readiness futures mapping`. Архитектурная граница подтверждена в обоих направлениях.

---

## 16. STRICT SPOT READINESS / CONTRACT EXPIRY CHECKPOINT

**Дата:** 26.08.2026  
**Код и regression coverage:** `ae4a5ae8be9971b3a6f33bca9dc171e3cc5b3812` / `e5ca518c43cb0749eac7c5a98f2056460fe3519b`

Усилена граница `SPOT → FUTURES MAPPING` без изменения канонического принципа SPOT-first:

- futures mapping теперь разрешён только для `READY` или `CONFIRMED` SPOT setup;
- `WATCH + trigger` больше не считается достаточной готовностью для привязки фьючерса;
- направление setup обязано совпадать с направлением SPOT-кандидата (`setup_direction == direction`);
- базовый `FuturesMorningRadarService` исключает контракты с `3` и менее календарными днями до экспирации, синхронизируя это правило с двухфазным production pipeline;
- `days_to_expiry` вычисляется и сохраняется явно для выбранного справочного контракта;
- добавлены regression tests для строгого readiness gate, несовпадения направления и expiry safety;
- SPOT eligibility, score, RS, setup и ranking по-прежнему не зависят от futures metrics.

**Аудиторский вывод:** mapping boundary теперь формально закрыта с двух сторон: недостаточно просто иметь trigger — требуется каноническая `READY/CONFIRMED` готовность и согласованное направление; кроме того, технически непригодный контракт, находящийся в пределах трёх дней до экспирации, не может стать reference mapping.
