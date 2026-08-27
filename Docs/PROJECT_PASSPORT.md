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

Historical checkpoint хранит `spot_price`, `trigger_active`, `trigger_state` и canonical `signal_state`.

### Historical canonical boundary — 27.08.2026

`HistoricalUniverseReplayService` больше не определяет readiness отдельной формулой `setup_state + trigger`. Каждый historical checkpoint проходит через тот же network-free `lifecycle_state()` из `spot_signal_contract.py`, что и live lifecycle.

Historical replay теперь сохраняет canonical lifecycle evidence, включая `signal_state_reason`, `trigger_crossed`, `trigger_invalidated` и stability fields. Compatibility helper `_spot_trigger_active()` остаётся только projection на canonical contract и не содержит собственной directional логики.

Это закрывает критическое расхождение между live и historical readiness boundary без изменения публичной pipeline version.

---

## 12. TEST ARCHITECTURE

Deterministic regression tests не должны зависеть от действующего BCS refresh token, сети или live market-data. Runtime BCS authorization относится только к production/live-data контуру.

Текущий regression matrix canonical contract включает:

- directional RS;
- LONG/SHORT trigger activation;
- trigger crossing;
- invalid trigger;
- WAIT/WATCH/ARMED/READY/CONFIRMED lifecycle;
- WAIT setup не может стать READY только из-за активной цены;
- stability requirement;
- invalidation;
- запрет возврата из INVALIDATED без нового setup;
- anti-regression READY при шумовом наблюдении;
- quality aggregation;
- live/historical trigger parity;
- historical canonical lifecycle projection;
- historical monotonic lifecycle across checkpoints;
- historical terminal invalidation without new setup.

После lifecycle hardening тестовые ожидания pipeline приведены в соответствие с новой семантикой: `WATCH + trigger не достигнут = ARMED`, а `WAIT = WAIT`.

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

### Lifecycle boundary correction

27.08.2026 устранена ошибка, при которой `setup_state=WAIT` мог становиться `READY` только из-за активной цены. Теперь `WAIT` остаётся `WAIT`, а `WATCH` с неактивным trigger корректно отображается как `ARMED`.

### Historical canonical boundary

27.08.2026 historical replay переведён на canonical `lifecycle_state()` из `spot_signal_contract.py`. Локальная readiness/trigger формула удалена; historical checkpoints теперь несут единый canonical lifecycle и reason trail. Добавлены regression tests для ARMED, READY, monotonicity и terminal invalidation.

---

## 14. CURRENT CHECKPOINT — HISTORICAL CANONICAL BOUNDARY CLOSED

**Дата:** 27.08.2026  
**Commits:** `526b5dd`, `27ae47c`.

### Что сделано

1. Historical replay импортирует canonical `lifecycle_state()`.
2. Каждый replay checkpoint декорируется canonical lifecycle.
3. Historical `_first_ready()` больше не содержит собственной readiness формулы.
4. Historical `_spot_trigger_active()` стал compatibility projection на canonical contract.
5. Historical result сохраняет `signal_state`, `trigger_state` и `signal_state_reason`.
6. Проверяется monotonic lifecycle между checkpoint-ами.
7. Terminal invalidation не может самопроизвольно вернуться в READY/CONFIRMED.
8. Futures boundary не затронут и остаётся post-SPOT mapping only.
9. Regression coverage расширен историческим lifecycle.

### Архитектурный результат

```text
LIVE SPOT
    │
    ├──────────────┐
    │              │
    ▼              ▼
CANONICAL SPOT SIGNAL CONTRACT
    ▲              ▲
    │              │
HISTORICAL REPLAY ┘
    │
    ▼
READY / CONFIRMED
    │
    ▼
FUTURES MAPPING ONLY
```

Теперь live и historical используют один lifecycle decision boundary.

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

Следующий уровень — **профессиональный SETUP QUALITY engine**:

1. отделить structural setup quality от простого `setup_state`;
2. формализовать impulse, retracement, consolidation/stabilization и breakout/rebound quality;
3. исключить двойной учёт одного и того же price evidence;
4. связать quality с canonical contract без переноса решения во futures;
5. добавить LONG/SHORT и historical/live regression matrix;
6. затем перейти к trigger re-arming / anti-churn tuning.

Не менять публичный pipeline version без отдельного решения.

---

## 17. SAFETY / PRODUCT BOUNDARY

Trader_7_12 Pro не является системой автоматического исполнения сделок.

Нет order execution, SL/TP engine, portfolio sizing, automatic position management или futures confirmation как торгового сигнала.

Futures остаётся `MAPPING ONLY`.
