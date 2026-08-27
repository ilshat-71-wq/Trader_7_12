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

На уровне setup сохраняются `WAIT`, `WATCH`, `READY`, `CONFIRMED`. На уровне canonical signal lifecycle используются более детальные состояния `WAIT`, `WATCH`, `ARMED`, `READY`, `CONFIRMED`, а также terminal `INVALIDATED`.

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

Чистый deterministic contract содержит нормализацию direction/setup, directional RS, trigger presence, directional trigger activation/crossing, invalidation, lifecycle state и прозрачную quality aggregation.

Контракт не обращается к BCS, сети, futures или live market-data.

### Production integration — 27.08.2026

`MorningTradingPipelineService` использует canonical contract непосредственно для:

- directional RS;
- trigger presence;
- directional trigger activation;
- final SPOT readiness/lifecycle state.

Публичный pipeline version остаётся `1.4`: это консолидация критических правил без изменения публичного version contract.

### Canonical lifecycle — 27.08.2026

Один setup lifecycle развивается детерминированно:

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

`INVALIDATED` является terminal state текущего lifecycle. После invalidation возврат в `READY/CONFIRMED` запрещён без явного `new_setup=True`.

Ключевые инварианты:

1. trigger level и trigger activation разделены;
2. LONG/SHORT activation направленная;
3. crossing фиксируется отдельно от простого нахождения цены за уровнем;
4. stability requirement учитывается отдельно;
5. старый lifecycle не переходит назад из-за единичного шумового наблюдения;
6. futures не участвуют в lifecycle;
7. новый setup должен явно начать новый lifecycle.

---

## 7. SETUP QUALITY

Качество setup отделяется от самого факта существования setup.

Canonical contract допускает прозрачную агрегацию:

- базовое `setup_quality` — 60%;
- `breakout_quality` — 20%;
- `structure_quality` — 20%.

Все компоненты ограничиваются диапазоном `0..100`. Если дополнительные компоненты не переданы, сохраняется базовый setup quality без искусственного ухудшения.

Это подготовительный слой для дальнейшего профессионального quality engine; существующий breakout service пока не объявляется полной confirmation-моделью.

---

## 8. RANKING

Основной ranking score — `candidate_score`, затем session-level `opportunity_score`.

Directional RS используется как tie-break:

- LONG → больший RS выше;
- SHORT → более отрицательный RS выше.

TOP ограничен тремя кандидатами и не заполняется искусственно. Futures turnover, price, spread, expiry и confirmation не входят в SPOT ranking.

---

## 9. FUTURES MAPPING BOUNDARY

Futures — только reference mapping выбранного SPOT-актива.

Mapping разрешён только после:

1. `setup_state ∈ {READY, CONFIRMED}`;
2. `setup_direction == direction`;
3. валидного trigger;
4. фактической directional trigger activation.

Контракты с `days_to_expiry <= 3` исключаются.

> **SPOT READY + неактивный trigger не может вызвать futures mapping.**

---

## 10. EVENT-RISK GATE

`moex_event_risk` остаётся жёстким SPOT eligibility gate. Сильные money/activity/RS/setup данные не могут его обойти.

---

## 11. HISTORICAL REPLAY

Historical replay — `READ ONLY / NO ORDERS`.

Исторический SPOT candidate формируется и ранжируется до futures lookup. Futures не могут скрыто изменить historical SPOT eligibility или ranking.

Historical trigger activation использует ту же directional модель:

```text
LONG  → spot_price >= entry_trigger
SHORT → spot_price <= entry_trigger
```

Historical checkpoint хранит `spot_price` и `trigger_active`.

Canonical lifecycle является network-free и предназначен для общего применения live/historical boundary; дальнейшая задача — заменить оставшиеся локальные historical readiness checks прямым использованием canonical lifecycle.

---

## 12. TEST ARCHITECTURE

Deterministic regression tests не должны зависеть от действующего BCS refresh token, сети или live market-data. Runtime BCS authorization относится только к production/live-data контуру.

Текущий regression matrix canonical contract включает:

- directional RS;
- LONG/SHORT trigger activation;
- trigger crossing;
- invalid trigger;
- WAIT/WATCH/ARMED/READY/CONFIRMED lifecycle;
- stability requirement;
- invalidation;
- запрет возврата из INVALIDATED без нового setup;
- anti-regression READY при шумовом наблюдении;
- quality aggregation;
- live/historical trigger parity.

---

## 13. VALIDATED CHECKPOINTS

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

### Canonical lifecycle hardening

27.08.2026 canonical contract расширен до строгой deterministic lifecycle-модели с `WATCH → ARMED → READY → CONFIRMED`, directional crossing, invalidation и explicit new-setup reset. Добавлена regression matrix для этих правил.

---

## 14. CURRENT CHECKPOINT — CANONICAL SPOT LIFECYCLE HARDENED

**Дата:** 27.08.2026  
**Commits:** `fcca362`, `eb2fdee9`.

### Что сделано

1. `spot_signal_contract.py` получил canonical lifecycle semantics.
2. Разделены trigger presence, activation и crossing.
3. Добавлен directional invalidation.
4. `INVALIDATED` стал terminal состоянием текущего lifecycle.
5. Повторная активация разрешается только через явный новый setup.
6. Stability requirement остаётся отдельным параметром deterministic contract.
7. Добавлена прозрачная bounded quality aggregation.
8. Добавлена regression matrix для state machine, invalidation, crossing и anti-regression.

### Архитектурный результат

```text
CANONICAL SPOT CONTRACT
        ↓
STATE / TRIGGER LIFECYCLE
        ↓
READY / CONFIRMED
        ↓
FUTURES MAPPING ONLY
```

Это не изменение торговой стратегии и не разрешение на автоматическую торговлю. Это укрепление deterministic analytical boundary.

---

## 15. RELEASE / WORKFLOW RULE

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

## 16. NEXT ENGINEERING PRIORITY

Следующий уровень — **production/historical boundary audit**:

1. убрать оставшиеся локальные readiness/trigger rules из `historical_universe_replay_service.py`, `historical_candidate_ranker_service.py`, futures adapters и других boundary-модулей там, где они дублируют canonical contract;
2. подключить canonical lifecycle к historical replay без изменения его фактической семантики;
3. добавить contract-level audit trail с причиной каждого перехода;
4. затем перейти к профессиональному SETUP QUALITY / breakout quality engine;
5. после этого — к scoring и anti-churn tuning на regression matrix.

Не менять публичный pipeline version без отдельного решения.

---

## 17. SAFETY / PRODUCT BOUNDARY

Trader_7_12 Pro не является системой автоматического исполнения сделок.

Нет order execution, SL/TP engine, portfolio sizing, automatic position management или futures confirmation как торгового сигнала.

Futures остаётся `MAPPING ONLY`.
