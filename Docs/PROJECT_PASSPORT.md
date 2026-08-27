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

`trigger_transition()` разделяет `trigger_crossed`, `trigger_active`, `trigger_state`, `trigger_rearmed` и `trigger_invalidated`.

Обычный откат после activation не является invalidation. Он может re-arm trigger, но не уничтожает lifecycle.

---

## 6. SETUP QUALITY

Файл: `Program/services/setup_quality_service.py`.

Quality отделена от detection и lifecycle. Canonical aggregation использует bounded компоненты `0..100`; отдельный SetupQualityService использует geometry 30%, candle 25%, rejection 20%, continuation 25%.

`SetupEngine.analyze()` обогащает setup candidate quality на том же подготовленном candle window. Quality deterministic/network-free, не переводит setup в READY/CONFIRMED и не меняет earliest READY selection.

---

## 7. RANKING

Основной ranking score — `candidate_score`, затем session-level `opportunity_score`.

Directional RS используется как tie-break. TOP ограничен тремя кандидатами и не заполняется искусственно. Futures metrics не входят в SPOT ranking.

Quality — прозрачный bounded SPOT input с небольшим setup bonus и не может заменить activity, money или directional RS. Session ranking deterministic.

---

## 8. ANTI-CHURN STABILITY

`MorningTradingPipelineService` использует `SIGNAL_STABILITY_OBSERVATIONS = 2`.

```text
1-е последовательное active observation → ARMED
2-е последовательное active observation → READY
trigger inactive → stability counter reset
READY + обычный transient retreat → READY
explicit invalidation → INVALIDATED
new_setup=True → новый lifecycle без старой стабильности
```

Stability не меняет SPOT ranking, candidate score, RS, setup detection или futures eligibility. Historical replay использует ту же границу.

---

## 9. FUTURES MAPPING BOUNDARY

Futures — только reference mapping выбранного SPOT-актива.

До `signal_state ∈ {READY, CONFIRMED}` futures mapping data очищаются из результата. После canonical READY/CONFIRMED mapping может быть показан как reference-only.

Дополнительные ограничения: direction должен совпадать с setup direction; trigger должен быть directional active; `days_to_expiry <= 3` исключается; futures не участвуют в SPOT eligibility, direction, RS, setup, readiness или ranking.

`futures_confirmation` всегда `NOT_APPLICABLE`; futures не подтверждают SPOT signal.

---

## 10. EVENT-RISK GATE

`moex_event_risk` остаётся жёстким SPOT eligibility gate и проверяется до candidate formation/mapping.

---

## 11. HISTORICAL REPLAY

Historical replay — `READ ONLY / NO ORDERS`.

Исторический SPOT candidate формируется и ранжируется до futures lookup. Futures не могут изменить historical SPOT eligibility или ranking.

`HistoricalUniverseReplayService` использует тот же network-free `lifecycle_state()` из canonical contract. Historical anti-churn parity повторяет live boundary, включая new-setup reset.

---

## 12. TEST ARCHITECTURE

Regression tests deterministic и не зависят от BCS refresh token, сети или live market-data.

Покрываются canonical lifecycle, trigger crossing/re-arm/invalidation, stability, setup quality, SetupEngine parity, live/historical parity, SPOT→futures boundary, event-risk, expiry, RS tie-break и независимость SPOT ranking от futures reference data.

CI проверяет фактический repository test inventory через `pytest -q Program`.

---

## 13. REPOSITORY HYGIENE / TEST INVENTORY — 27.08.2026

Обнаружен legacy-каталог `Program/tests/`. Его содержимое не было слепо удалено: четыре полезных набора regression coverage перенесены в канонический корень `Program/`:

- `test_futures_selection_and_market_universe.py`;
- `test_historical_candidate_ranker_service.py`;
- `test_moex_index_universe_service.py`;
- `test_spot_universe_service.py`.

После переноса старые копии из `Program/tests/` удалены. Production services не удалялись, поскольку по текущему inventory они являются частью архитектуры или используются существующими тестами/runners.

Также устранён единственный обнаруженный pytest collection warning: тестовый harness `TestableRadar` переименован в `RadarHarness`, поскольку pytest ошибочно пытался собирать helper-class с `__init__` как test class.

Локальная рабочая правка исторического теста сохранена в перенесённом canonical test: readiness/mapping fixtures теперь используют действительно активный trigger boundary (`spot_price == entry_trigger`).

---

## 14. VALIDATED CHECKPOINTS — 27.08.2026

### Canonical lifecycle hardening
Deterministic `WATCH → ARMED → READY → CONFIRMED`, directional crossing, terminal invalidation и explicit new-setup reset.

### Historical canonical boundary
Historical replay переведён на canonical lifecycle contract.

### Setup quality layer
Создан отдельный deterministic `SetupQualityService` с bounded structural scoring.

### SetupEngine quality integration
Quality интегрирована в SetupEngine как enrichment без изменения detection/lifecycle semantics.

### Live anti-churn
Введён двухнаблюдательный `ARMED → READY` gate.

### Historical/live stability parity
Historical replay повторяет live stability boundary и new-setup reset.

### Canonical futures mapping boundary
Финальный live pipeline gate не позволяет показать futures mapping до canonical `READY/CONFIRMED`.

### Repository CI inventory correction
GitHub Actions переведён на фактический repository inventory:

```text
python -m compileall -q Program
PYTHONPATH=Program python -m pytest -q Program
```

### Repository cleanup checkpoint — 27.08.2026
Legacy nested tests migrated into the canonical `Program/test_*.py` inventory, stale copies removed, pytest collection warning eliminated. No additional branch created.

---

## 15. CURRENT CHECKPOINT

**Checkpoint:** Full repository deterministic audit / Release Candidate preparation  
**Дата:** 27.08.2026  
**Рабочая ветка:** `main`

### Текущий статус

До cleanup полный repository inventory показывал **163 collected tests**, из них **161 passed / 2 failed / 1 warning**. Два failure были не production regression, а stale historical fixtures, которые противоречили canonical directional trigger boundary. Оба fixture исправлены и перенесены в canonical root inventory.

После cleanup необходимо локально подтвердить новый полный inventory. Ожидаемый результат — отсутствие `Program/tests`, отсутствие collection warning и полный зелёный repository regression.

### Следующий обязательный уровень

**Release Candidate validation:**

1. `git pull --ff-only`;
2. compile всего `Program`;
3. полный `PYTHONPATH=Program python3 -m pytest -q Program`;
4. убедиться, что legacy `Program/tests` отсутствует;
5. проверить отсутствие warnings/errors;
6. если всё зелёное — зафиксировать RC checkpoint и перейти к финальной эксплуатационной проверке launch/UI/data path.

---

## 16. RELEASE / WORKFLOW RULE

После каждого законченного уровня:

1. изменения сохраняются в GitHub `main`;
2. commit фиксируется;
3. `PROJECT_PASSPORT.md` обновляется;
4. compile/regression checks проходят на локальном iMac;
5. пользователь делает один `git pull --ff-only`;
6. reinstall требуется только если изменены app bundle/launcher/icon или другой локально собираемый компонент.

**Канонический паспорт:** `Docs/PROJECT_PASSPORT.md`.
**Рабочая ветка:** только `main`.
**Дополнительные ветки:** не создаём.
