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
TRIGGER ACTIVE
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

Состояния: `WAIT`, `WATCH`, `READY`, `CONFIRMED`.

`READY/CONFIRMED` — аналитические состояния, не торговая команда.

---

## 5. TRIGGER INVARIANT

> **Trigger level ≠ trigger activation.**

```text
LONG  → spot_price >= entry_trigger
SHORT → spot_price <= entry_trigger
```

Цена до trigger не считается фактически активировавшей сценарий.

---

## 6. CANONICAL SPOT SIGNAL CONTRACT

Файл: `Program/services/spot_signal_contract.py`.

Чистый deterministic contract содержит `normalize_direction()`, `directional_rs()`, `trigger_present()`, `trigger_active()` и `readiness_state()`.

Контракт не обращается к BCS, сети, futures или live market-data.

### Production integration — 27.08.2026

`MorningTradingPipelineService` использует canonical contract непосредственно для:

- directional RS;
- trigger presence;
- directional trigger activation;
- final SPOT readiness state.

Публичный pipeline version остаётся `1.4`: это консолидация критических правил без изменения публичного version contract.

---

## 7. RANKING

Основной ranking score — `candidate_score`, затем session-level `opportunity_score`.

Directional RS используется как tie-break:

- LONG → больший RS выше;
- SHORT → более отрицательный RS выше.

TOP ограничен тремя кандидатами и не заполняется искусственно. Futures turnover, price, spread, expiry и confirmation не входят в SPOT ranking.

---

## 8. FUTURES MAPPING BOUNDARY

Futures — только reference mapping выбранного SPOT-актива.

Mapping разрешён только после:

1. `setup_state ∈ {READY, CONFIRMED}`;
2. `setup_direction == direction`;
3. валидного trigger;
4. фактической directional trigger activation.

Контракты с `days_to_expiry <= 3` исключаются.

> **SPOT READY + неактивный trigger не может вызвать futures mapping.**

---

## 9. EVENT-RISK GATE

`moex_event_risk` остаётся жёстким SPOT eligibility gate. Сильные money/activity/RS/setup данные не могут его обойти.

---

## 10. HISTORICAL REPLAY

Historical replay — `READ ONLY / NO ORDERS`.

Исторический SPOT candidate формируется и ранжируется до futures lookup. Futures не могут скрыто изменить historical SPOT eligibility или ranking.

Historical trigger activation использует ту же directional модель:

```text
LONG  → spot_price >= entry_trigger
SHORT → spot_price <= entry_trigger
```

Historical checkpoint хранит `spot_price` и `trigger_active`.

---

## 11. TEST ARCHITECTURE

Deterministic regression tests не должны зависеть от действующего BCS refresh token, сети или live market-data. Runtime BCS authorization относится только к production/live-data контуру.

Покрываются SPOT pipeline, instrument radar, candidate score, directional RS ranking, event-risk gate, readiness, trigger activation, futures mapping boundary, expiry safety и historical/production parity.

---

## 12. VALIDATED CHECKPOINTS

### SPOT-first ranking

Futures metrics исключены из SPOT score/ranking. Production и historical paths сохраняют SPOT-first boundary.

### Trigger activation

27.08.2026 закрыто различие между trigger level и trigger active. LONG/SHORT activation направленная и SPOT-only.

### Offline regression isolation

27.08.2026 instrument radar unit tests изолированы от BCS authorization.

### Historical parity

27.08.2026 historical replay не создаёт `ready_time` до фактической SPOT trigger activation.

### Directional RS consistency

27.08.2026 session ranking использует directional RS tie-break: более сильная поддержка текущего направления всегда выше.

---

## 13. CURRENT CHECKPOINT — CANONICAL CONTRACT ENFORCED IN LIVE PIPELINE

**Дата:** 27.08.2026  
**Commits:** `1102d54`, `2cfa40a`, `53edc52`.

### Что сделано

1. Live `MorningTradingPipelineService` подключён к `spot_signal_contract.py`.
2. Дублированные реализации directional RS / trigger presence / trigger activation заменены вызовами canonical helpers.
3. Readiness в live pipeline вычисляется через `readiness_state()`.
4. Добавлена regression-проверка live `_advance_signal_state()` против canonical semantics.
5. Existing historical trigger-parity coverage сохранена.

### Архитектурный результат

```text
CANONICAL SPOT CONTRACT
        ↓
LIVE PIPELINE
        ↓
READY / CONFIRMED
        ↓
FUTURES MAPPING ONLY
```

Это повышает зрелость проекта: критические правила сигнала имеют один явный deterministic source of truth на live pipeline boundary.

---

## 14. RELEASE / WORKFLOW RULE

После каждого законченного уровня:

1. изменения сохраняются в GitHub `main`;
2. commit фиксируется;
3. `PROJECT_PASSPORT.md` обновляется;
4. проходят compile/regression checks;
5. пользователь делает один локальный `git pull`;
6. reinstall требуется только если изменены app bundle/launcher/icon или другой локально собираемый компонент.

**Канонический паспорт:** `Docs/PROJECT_PASSPORT.md`  
**Единственная рабочая ветка:** `main`

---

## 15. NEXT ENGINEERING PRIORITY

Следующий уровень: довести canonical SPOT contract до полной production/historical boundary — убрать оставшиеся дублирующие trigger/readiness правила из historical/futures adapters и добавить contract-level audit, показывающий причину каждого `WAIT → WATCH → READY → CONFIRMED` перехода без обращения к futures.

---

## 16. SAFETY / PRODUCT BOUNDARY

Trader_7_12 Pro не является системой автоматического исполнения сделок.

Нет order execution, SL/TP engine, portfolio sizing, automatic position management или futures confirmation как торгового сигнала.

Futures остаётся `MAPPING ONLY`.
