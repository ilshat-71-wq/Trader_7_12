# TRADER_7_12 PRO — PROJECT PASSPORT

**Дата актуализации:** 27.08.2026  
**Репозиторий:** `ilshat-71-wq/Trader_7_12`  
**Ветка:** `main`  
**Назначение:** read-only SPOT-first opportunity scanner для самостоятельной intraday-торговли фьючерсами Московской биржи.

> Сканер находит ГДЕ смотреть. Пользователь самостоятельно выбирает фьючерс, график, вход и риск. Исполнение ордеров, SL/TP и position sizing отсутствуют.

---

## 1. КАНОНИЧЕСКАЯ АРХИТЕКТУРА

```text
SPOT
 ↓
MONEY / ACTIVITY
 ↓
DIRECTION / DAILY TREND
 ↓
RS vs IMOEX2 / IRUS2
 ↓
H1 STRUCTURE + M5 SETUP
 ↓
TRIGGER LEVEL
 ↓
TRIGGER ACTIVE / CROSSED
 ↓
ANTI-CHURN STABILITY
 ↓
READY / CONFIRMED
 ↓
TOP 2–3 SPOT WATCHLIST
 ↓
FUTURES MAPPING ONLY
```

Фьючерс не определяет direction, RS, eligibility, setup, trigger, readiness или SPOT ranking.

---

## 2. SPOT MONEY / ACTIVITY

Используются `price × volume`, текущий session money volume, средний оборот завершённых дней, money per minute и activity ratio относительно ожидаемой активности к текущему моменту.

Абсолютный оборот сам по себе не делает инструмент лидером: важна активность относительно собственной нормы.

---

## 3. MARKET BENCHMARK / RS

Benchmark российского рынка: `IMOEX2 / IRUS2`.

`relative_strength = instrument_return - benchmark_return`.

- `STRONGER`: RS ≥ +0.20 п.п.;
- `WEAKER`: RS ≤ −0.20 п.п.;
- `NEUTRAL`: промежуточная зона;
- `RS_UNAVAILABLE`: обязательные benchmark data отсутствуют.

Direction и RS должны быть согласованы: LONG + STRONGER, SHORT + WEAKER. Фиктивный RS запрещён.

---

## 4. SETUP / READINESS

H1 задаёт контекст, M5 формирует сценарий.

LONG: `H1 up → impulse → first pullback → stabilization → continuation`  
SHORT: `H1 down → impulse → first rebound → stabilization → continuation`

На уровне setup сохраняются `WAIT`, `WATCH`, `READY`, `CONFIRMED`. На уровне canonical signal lifecycle используются `WAIT`, `WATCH`, `ARMED`, `READY`, `CONFIRMED`, а также terminal `INVALIDATED`.

`READY/CONFIRMED` — аналитические состояния, не торговая команда.

---

## 5. CANONICAL SPOT SIGNAL CONTRACT

Файл: `Program/services/spot_signal_contract.py`.

Это deterministic network-free contract для нормализации direction/setup, directional RS, trigger presence, directional activation/crossing, trigger transition, invalidation, lifecycle и quality aggregation. Контракт не обращается к BCS, сети, futures или live market-data.

### Lifecycle

```text
WAIT
 ↓
WATCH
 ↓
ARMED
 ↓
READY
 ↓
CONFIRMED
```

`INVALIDATED` — terminal state текущего lifecycle. После invalidation возврат в `READY/CONFIRMED` запрещён без явного `new_setup=True`.

### Trigger invariant

> **Trigger level ≠ trigger activation.**

```text
LONG  → spot_price >= entry_trigger
SHORT → spot_price <= entry_trigger
```

`trigger_transition()` разделяет:

- `trigger_crossed` — edge transition на текущем observation;
- `trigger_active` — level-based состояние;
- `trigger_state` — `WAITING / ARMED / ACTIVE / INVALIDATED`;
- `trigger_rearmed` — возврат из ACTIVE в ARMED без invalidation;
- `trigger_invalidated` — terminal risk condition.

Обычный откат после activation не является invalidation. Он может re-arm trigger, но не уничтожает lifecycle.

---

## 6. SETUP QUALITY

Файл: `Program/services/setup_quality_service.py`.

Quality отделена от detection и lifecycle. Canonical aggregation использует bounded компоненты `0..100`; отдельный SetupQualityService использует:

- `geometry` — 30%;
- `candle` — 25%;
- `rejection` — 20%;
- `continuation` — 25%.

Результат сохраняется как `setup_quality_score`, `quality_components`, `setup_quality_reasons`.

`SetupEngine.analyze()` обогащает setup candidate quality на том же подготовленном candle window. Quality deterministic/network-free, не переводит setup в READY/CONFIRMED и не меняет earliest READY selection.

Для идентичного candle window regression защищает повторяемость score/components/reasons и отсутствие скрытой зависимости от внешнего состояния.

---

## 7. RANKING

Основной ranking score — `candidate_score`, затем session-level `opportunity_score`.

Directional RS используется как tie-break. TOP ограничен тремя кандидатами и не заполняется искусственно. Futures metrics не входят в SPOT ranking.

Quality присутствует как прозрачный SPOT quality input; его влияние ограничено небольшим bounded setup bonus в `candidate_score` и не может заменить activity, money или directional RS. Session ranking остаётся deterministic.

---

## 8. ANTI-CHURN STABILITY

`MorningTradingPipelineService` использует `SIGNAL_STABILITY_OBSERVATIONS = 2`.

Правило:

```text
1-е последовательное active observation → ARMED
2-е последовательное active observation → READY
trigger inactive → stability counter reset
READY + обычный transient retreat → READY
explicit invalidation → INVALIDATED
new_setup=True → новый lifecycle без старой стабильности
```

Stability не меняет SPOT ranking, candidate score, RS, setup detection или futures eligibility. Это исключительно lifecycle anti-noise gate.

Historical replay использует ту же границу, обеспечивая live/historical parity.

---

## 9. FUTURES MAPPING BOUNDARY

Futures — только reference mapping выбранного SPOT-актива.

Первичный radar может вычислять возможный mapping, но пользовательский live pipeline имеет финальный canonical gate. До `signal_state ∈ {READY, CONFIRMED}` futures mapping data очищаются из результата и получают:

`futures_selection_reason = WAITING_FOR_CANONICAL_SPOT_READINESS`.

После canonical READY/CONFIRMED mapping может быть показан как reference-only.

Дополнительные ограничения:

- direction должен совпадать с setup direction;
- trigger должен быть directional active;
- `days_to_expiry <= 3` исключается;
- futures не участвуют в SPOT eligibility, direction, RS, setup, readiness или ranking.

`futures_confirmation` всегда `NOT_APPLICABLE`; futures не подтверждают SPOT signal.

---

## 10. EVENT-RISK GATE

`moex_event_risk` остаётся жёстким SPOT eligibility gate и проверяется до candidate formation/mapping.

---

## 11. HISTORICAL REPLAY

Historical replay — `READ ONLY / NO ORDERS`.

Исторический SPOT candidate формируется и ранжируется до futures lookup. Futures не могут изменить historical SPOT eligibility или ranking.

`HistoricalUniverseReplayService` использует тот же network-free `lifecycle_state()` из canonical contract. Checkpoint хранит canonical lifecycle evidence, включая `signal_state_reason`, `trigger_crossed`, `trigger_invalidated` и stability fields.

Historical anti-churn parity повторяет live boundary: первое active observation — ARMED, второе — READY, потеря trigger сбрасывает counter, transient retreat после READY не откатывает lifecycle. `new_setup=True` начинает новый lifecycle и не наследует старую стабильность.

---

## 12. TEST ARCHITECTURE

Regression tests deterministic и не зависят от BCS refresh token, сети или live market-data.

Покрываются:

- canonical direction / RS;
- LONG/SHORT trigger activation;
- trigger crossing / re-arm / invalidation;
- WAIT/WATCH/ARMED/READY/CONFIRMED lifecycle;
- stability и new-setup reset;
- setup quality и incomplete OHLC;
- SetupEngine quality integration/parity;
- live anti-churn;
- historical/live stability parity;
- SPOT → futures mapping boundary;
- event-risk gate;
- expiry filtering;
- directional RS tie-break;
- сохранение SPOT ranking независимо от futures reference data.

CI должен проверять фактический repository test inventory через `pytest -q Program`, а не несуществующий каталог `Program/tests`.

---

## 13. VALIDATED CHECKPOINTS — 27.08.2026

### Canonical lifecycle hardening

Deterministic `WATCH → ARMED → READY → CONFIRMED`, directional crossing, terminal invalidation и explicit new-setup reset.

### Lifecycle boundary correction

`setup_state=WAIT` не становится READY только из-за активной цены; trigger level и trigger activation разделены.

### Historical canonical boundary

Historical replay переведён на canonical lifecycle contract.

### Setup quality layer

Создан отдельный deterministic `SetupQualityService` с bounded structural scoring.

### SetupEngine quality integration

Quality интегрирована в SetupEngine как enrichment без изменения detection/lifecycle semantics.

### Quality parity baseline

Повторный расчёт на идентичном candle window deterministic; внешнее состояние не влияет.

### Live anti-churn

Введён двухнаблюдательный `ARMED → READY` gate.

### Historical/live stability parity

Historical replay повторяет live stability boundary и new-setup reset.

### Canonical futures mapping boundary — 27.08.2026

Финальный live pipeline gate теперь не позволяет показать futures mapping до canonical `READY/CONFIRMED`. Это закрывает output-level parity gap между stateful lifecycle и reference mapping.

### Repository CI inventory correction — 27.08.2026

Обнаружено, что GitHub Actions workflow ссылался на `Program/tests`, тогда как фактический repository test inventory находится в `Program/test_*.py` и подкаталогах проекта. Workflow исправлен на:

```text
python -m compileall -q Program
PYTHONPATH=Program python -m pytest -q Program
```

Это делает CI-цель соответствующей фактическому репозиторию и предотвращает ложный зелёный/сломанный validation path из-за неверного каталога.

---

## 14. CURRENT CHECKPOINT

**Checkpoint:** Repository-wide deterministic validation path hardening  
**Дата:** 27.08.2026  
**Рабочая ветка:** `main`  
**Последний commit уровня:** `86ba350ad005007638d22fa5a868f1aae9f4c44d`

### Что сделано

1. Проверен фактический repository test inventory.
2. Обнаружена stale CI-конфигурация с несуществующим `Program/tests`.
3. GitHub Actions переведён на `compileall -q Program`.
4. GitHub Actions переведён на полный `PYTHONPATH=Program python -m pytest -q Program`.
5. `PROJECT_PASSPORT.md` обновлён как единственный канонический MD-документ проекта.
6. Все изменения сохранены в `main` без создания дополнительных веток.

### Следующий обязательный уровень

**Full repository deterministic audit / Release Candidate preparation:**

- локально выполнить полный `pytest -q Program`, а не только текущую целевую матрицу;
- проверить все legacy/standalone services и их тесты;
- выявить тесты, которые не входят в текущие lifecycle suites;
- проверить, что CI после исправления действительно проходит тот же полный inventory;
- устранить только реальные архитектурные gaps, не меняя каноническую SPOT-first semantics;
- после зелёного полного inventory зафиксировать Release Candidate checkpoint в этом паспорте.

---

## 15. RELEASE / WORKFLOW RULE

После каждого законченного уровня:

1. изменения сохраняются в GitHub `main`;
2. commit фиксируется;
3. `PROJECT_PASSPORT.md` обновляется;
4. compile/regression checks проходят на локальном iMac;
5. пользователь делает один `git pull --ff-only`;
6. reinstall требуется только если изменены app bundle/launcher/icon или другой локально собираемый компонент.

**Канонический паспорт:** `Docs/PROJECT_PASSPORT.md`.
