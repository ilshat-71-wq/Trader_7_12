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

`MorningTradingPipelineService` использует canonical contract непосредственно для directional RS, trigger presence, directional trigger activation и final SPOT readiness/lifecycle state.

Публичный pipeline version остаётся `1.4`.

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

Ключевые инварианты: trigger level и activation разделены; LONG/SHORT activation направленная; crossing фиксируется отдельно; stability учитывается отдельно; старый lifecycle не откатывается из-за шума; futures не участвуют; новый setup явно начинает новый lifecycle.

### Canonical trigger transition — 27.08.2026

Добавлена `trigger_transition()` как единая edge-aware projection для trigger lifecycle.

Она разделяет:

- `trigger_crossed` — факт перехода через trigger на текущем наблюдении;
- `trigger_active` — текущее level-based состояние;
- `trigger_state` — `WAITING / ARMED / ACTIVE / INVALIDATED`;
- `trigger_rearmed` — возврат из `ACTIVE` в `ARMED` без invalidation;
- `trigger_invalidated` — отдельный terminal risk condition.

Ключевой инвариант: **обычный откат цены после активации не равен invalidation**. Он может re-arm trigger, но не уничтожает setup lifecycle. Только explicit invalidation level переводит trigger в `INVALIDATED`; новый setup нужен для восстановления terminal signal lifecycle.

---

## 7. SETUP QUALITY

Качество setup отделяется от самого факта существования setup.

Canonical aggregation использует базовое `setup_quality` 60%, `breakout_quality` 20% и `structure_quality` 20%; компоненты ограничены `0..100`.

### Setup Quality Engine — 27.08.2026

Создан deterministic network-free `Program/services/setup_quality_service.py`. Он не меняет lifecycle и не может сам перевести setup в `READY/CONFIRMED`.

Компоненты:

- `geometry` — 30%;
- `candle` — 25%;
- `rejection` — 20%;
- `continuation` — 25%.

Сохраняются `setup_quality_score`, `quality_components` и `setup_quality_reasons`. Отсутствующие OHLC-данные не превращаются в искусственное качество.

### Setup Quality → SetupEngine integration — 27.08.2026

`SetupEngine.analyze()` теперь обогащает каждый setup candidate результатом canonical `SetupQualityService` на том же подготовленном candle window. Quality считается после формирования setup и не изменяет `setup_state`, trigger или выбор earliest READY setup.

Quality остаётся deterministic и network-free и пока не участвует автоматически в ranking. Это сохраняет разделение detection → quality → lifecycle.

### Quality projection parity hardening — 27.08.2026

Для одного и того же подготовленного candle window `SetupEngine.analyze()` обязан давать полностью детерминированные `setup_quality_score`, `quality_components` и `setup_quality_reasons`. Добавлена regression coverage, защищающая от скрытой зависимости quality от состояния процесса или внешних данных.

Дополнительно проверяется, что quality использует только переданный window и не меняется при повторном вычислении того же набора свечей. Это является базовой parity-гарантией перед подключением quality к более высоким слоям.

---

## 8. RANKING

Основной ranking score — `candidate_score`, затем session-level `opportunity_score`.

Directional RS используется как tie-break. TOP ограничен тремя кандидатами и не заполняется искусственно. Futures metrics не входят в SPOT ranking.

Quality пока является enrichment/tie-break information и не получает скрытого веса в `candidate_score` или `opportunity_score`.

---

## 9. FUTURES MAPPING BOUNDARY

Futures — только reference mapping выбранного SPOT-актива.

Mapping разрешён только после `setup_state ∈ {READY, CONFIRMED}`, согласованного direction, валидного trigger и фактической directional trigger activation. Контракты с `days_to_expiry <= 3` исключаются.

> **SPOT READY + неактивный trigger не может вызвать futures mapping.**

---

## 10. EVENT-RISK GATE

`moex_event_risk` остаётся жёстким SPOT eligibility gate.

---

## 11. HISTORICAL REPLAY

Historical replay — `READ ONLY / NO ORDERS`.

Исторический SPOT candidate формируется и ранжируется до futures lookup. Futures не могут изменить historical SPOT eligibility или ranking.

Historical trigger activation использует ту же directional модель. Checkpoint хранит `spot_price`, `trigger_active`, `trigger_state` и canonical `signal_state`.

### Historical canonical boundary — 27.08.2026

`HistoricalUniverseReplayService` больше не определяет readiness отдельной формулой `setup_state + trigger`. Каждый historical checkpoint проходит через тот же network-free `lifecycle_state()` из `spot_signal_contract.py`, что и live lifecycle.

Historical replay сохраняет canonical lifecycle evidence, включая `signal_state_reason`, `trigger_crossed`, `trigger_invalidated` и stability fields. Compatibility helper `_spot_trigger_active()` остаётся только projection на canonical contract.

---

## 12. TEST ARCHITECTURE

Deterministic regression tests не зависят от BCS refresh token, сети или live market-data.

Regression matrix canonical contract покрывает directional RS, LONG/SHORT trigger activation/crossing, invalid trigger, trigger transition/re-arming, WAIT/WATCH/ARMED/READY/CONFIRMED lifecycle, stability, invalidation, new-setup reset и live/historical parity.

`Program/test_setup_quality_service.py` покрывает bounded score, прозрачные компоненты, continuation и incomplete OHLC.

После SetupEngine integration дополнительно проверяется наличие quality у setup candidates, неизменность lifecycle, использование только доступного candle window, сохранение earliest READY selection и отсутствие автоматического влияния quality на ranking.

Quality parity regression дополнительно проверяет повторяемость результата на идентичном window и отсутствие скрытого влияния внешнего состояния.

### Anti-churn stability regression — 27.08.2026

Live pipeline теперь требует **2 последовательных наблюдения с активным directional trigger** для перехода в `READY`.

Первое активное наблюдение остаётся `ARMED`; второе последовательное активное наблюдение переводит lifecycle в `READY`. Если trigger не активен, счётчик сбрасывается.

Стабильность не меняет ranking, candidate score, RS, setup detection или futures mapping boundary. Это исключительно lifecycle anti-noise gate.

---

## 13. VALIDATED CHECKPOINTS

### SPOT-first ranking

Futures metrics исключены из SPOT score/ranking.

### Trigger activation

27.08.2026 закрыто различие между trigger level и trigger active. LONG/SHORT activation направленная и SPOT-only.

### Offline regression isolation

27.08.2026 instrument radar unit tests изолированы от BCS authorization.

### Historical parity

27.08.2026 historical replay не создаёт `ready_time` до фактической SPOT trigger activation.

### Directional RS consistency

27.08.2026 session ranking использует directional RS tie-break.

### Canonical lifecycle hardening

27.08.2026 canonical contract расширен до deterministic `WATCH → ARMED → READY → CONFIRMED`, directional crossing, invalidation и explicit new-setup reset.

### Lifecycle boundary correction

27.08.2026 `setup_state=WAIT` больше не может стать READY только из-за активной цены; WATCH с неактивным trigger отображается как ARMED.

### Historical canonical boundary

27.08.2026 historical replay переведён на canonical `lifecycle_state()` и получил regression coverage для ARMED, READY, monotonicity и terminal invalidation.

### Setup quality layer

27.08.2026 создан отдельный canonical `SetupQualityService` с bounded structural scoring и offline regression matrix.

### SetupEngine quality integration

27.08.2026 `SetupEngine` интегрировал canonical `SetupQualityService`: setup detection остаётся владельцем setup state, quality является отдельным enrichment layer, lifecycle и ranking semantics не изменены.

### Canonical trigger transition

27.08.2026 введён `trigger_transition()` для единой edge-aware trigger projection. Crossing, active state, re-arm и invalidation теперь различаются явно; обычный откат после activation не считается invalidation.

### Quality projection parity baseline

27.08.2026 добавлена regression coverage для deterministic quality на идентичном candle window и защиты от скрытой зависимости от внешнего состояния. Production ranking не изменён.

### Anti-churn / stability hardening

27.08.2026 live pipeline получил двухнаблюдательный stability gate. Единичный активный trigger больше не переводит новый setup непосредственно в READY; требуется второе последовательное активное наблюдение. Existing READY lifecycle не откатывается из-за временного шумового наблюдения.

---

## 14. CURRENT CHECKPOINT — ANTI-CHURN / STABILITY HARDENING

**Дата:** 27.08.2026  
**Commit:** `723cfa9` + `ed17a5a`.

### Что сделано

1. `MorningTradingPipelineService.SIGNAL_STABILITY_OBSERVATIONS` повышен с `1` до `2`.
2. Первый активный trigger observation остаётся `ARMED`.
3. Второе последовательное активное observation переводит setup в `READY`.
4. Потеря trigger сбрасывает consecutive-active counter.
5. Existing `READY` lifecycle защищён от обратного перехода из-за обычного price noise.
6. Добавлена regression coverage для LONG/SHORT двухнаблюдательной активации.
7. Добавлен anti-churn regression для сохранения READY после transient observations.
8. SPOT ranking, quality и futures mapping semantics не изменены.
9. `PROJECT_PASSPORT.md` обновлён этим checkpoint.
10. Публичный pipeline version остаётся `1.4`.

### Следующий обязательный уровень

**End-to-end live ↔ historical parity audit.**

Нужно проверить, что одинаковая последовательность SPOT observations даёт одинаковый lifecycle в live pipeline и historical replay, включая stability counter, trigger crossing, re-arm и invalidation. После этого — ranking audit и финальный release audit.

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

## 16. PROJECT COMPLETION ROADMAP

Проект уже прошёл основную архитектурную фазу. До production-ready состояния остаются три инженерных блока:

1. **End-to-end parity** — финальная проверка live → historical на одинаковых входах без расхождений.
2. **Ranking / candidate audit** — проверка отсутствия двойного учёта quality/RS/activity и финальный SPOT ranking audit.
3. **Release audit** — полный offline regression, compile, dependency/import audit, futures mapping boundary, event-risk gate, documentation consistency и clean-main verification.

После этих блоков отдельный этап «архитектурной переделки» не планируется. Возможны только bug fixes и controlled calibration по фактическим данным.

---

## 17. SAFETY / PRODUCT BOUNDARY

Trader_7_12 Pro не является системой автоматического исполнения сделок.

Нет order execution, SL/TP engine, portfolio sizing, automatic position management или futures confirmation как торгового сигнала.

Futures остаётся `MAPPING ONLY`.
