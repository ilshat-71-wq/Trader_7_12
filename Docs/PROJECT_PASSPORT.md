# TRADER_7_12 PRO — PROJECT PASSPORT

**Дата актуализации:** 27.08.2026  
**Репозиторий:** `ilshat-71-wq/Trader_7_12`  
**Рабочая ветка:** `main`

---

## 1. ЦЕЛЬ ПРОЕКТА

Trader_7_12 Pro — read-only аналитический scanner/assistant для самостоятельной intraday-торговли фьючерсами Московской биржи.

Канонический принцип:

> **Сканер находит ГДЕ смотреть. Пользователь самостоятельно выбирает фьючерс, график, вход и риск.**

Исполнение ордеров, SL/TP и position sizing отсутствуют.

---

## 2. КАНОНИЧЕСКАЯ SPOT-FIRST АРХИТЕКТУРА

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

Фьючерс не определяет direction, RS, eligibility, setup, trigger, readiness или ranking.

---

## 3. SPOT MONEY / ACTIVITY

Основная метрика — `price × volume`.

Используются:

- текущий SPOT money volume;
- средний оборот завершённых дней;
- текущий session money volume;
- money per minute;
- activity ratio относительно ожидаемой активности к текущему моменту.

Абсолютный оборот сам по себе не делает инструмент лидером: важна активность относительно собственной нормы.

---

## 4. MARKET BENCHMARK / RS

Основной benchmark российского рынка — `IMOEX2 / IRUS2`.

`relative_strength = instrument_return - benchmark_return`.

- `STRONGER` — RS ≥ +0.20 п.п.;
- `WEAKER` — RS ≤ −0.20 п.п.;
- `NEUTRAL` — промежуточная зона;
- `RS_UNAVAILABLE` — обязательные benchmark data отсутствуют.

Direction и RS должны быть согласованы для качественного кандидата:

- LONG + STRONGER;
- SHORT + WEAKER.

Фиктивный RS запрещён.

---

## 5. SETUP / READINESS

Основной контекст — H1 SPOT. Формирование сценария — M5 SPOT.

LONG:

`H1 up → impulse → first pullback → stabilization → continuation`

SHORT:

`H1 down → impulse → first rebound → stabilization → continuation`

Состояния:

- `WAIT` — setup ещё не сформирован;
- `WATCH` — setup развивается;
- `READY` — setup сформирован и trigger фактически активирован;
- `CONFIRMED` — подтверждённый SPOT-сценарий.

`READY/CONFIRMED` не являются торговой командой.

---

## 6. TRIGGER INVARIANT

Ключевой invariant проекта:

> **Наличие trigger level ≠ trigger activation.**

Directional activation:

- LONG → `spot_price >= entry_trigger`;
- SHORT → `spot_price <= entry_trigger`.

Таким образом, цена, находящаяся до trigger, не может считаться фактически активировавшей сценарий.

---

## 7. RANKING

Итоговый ranking отвечает на вопрос:

> **Где сегодня одновременно есть деньги, активность, движение, сила/слабость и качественный SPOT context?**

`candidate_score` является основным ranking score. Setup quality выводится отдельно и не заменяет opportunity score.

Directional RS используется как tie-break:

- LONG → больший RS выше;
- SHORT → более отрицательный RS выше.

Futures turnover, price, spread, confirmation и expiry не входят в SPOT ranking.

TOP ограничен тремя кандидатами и не заполняется искусственно.

---

## 8. FUTURES MAPPING BOUNDARY

Futures — только reference mapping выбранного SPOT-актива.

Mapping разрешён только после прохождения всех SPOT eligibility gates и при одновременном выполнении:

1. `setup_state ∈ {READY, CONFIRMED}`;
2. `setup_direction == direction`;
3. trigger существует;
4. trigger фактически активирован по направлению.

`WAIT`, `WATCH` или `READY` с ещё не достигнутым trigger не могут вызвать futures mapping.

Контракты с `days_to_expiry <= 3` исключаются из reference mapping.

---

## 9. EVENT-RISK GATE

`moex_event_risk` остаётся жёстким SPOT eligibility gate.

Сильные money/activity/RS/setup данные не могут обойти event-risk rejection.

---

## 10. HISTORICAL REPLAY

Historical replay остаётся `READ ONLY / NO ORDERS`.

Исторический SPOT candidate формируется и ранжируется до futures lookup. Futures не могут скрыто изменить historical SPOT eligibility или ranking.

Parity invariant:

> Если два SPOT-кандидата имеют одинаковые SPOT evidence, изменение futures ticker, expiry, turnover, price или confirmation не должно менять их SPOT ranking.

---

## 11. TEST ARCHITECTURE

Детерминированные unit regression не должны зависеть от действующего BCS refresh token, сети или live market-data.

Runtime BCS authorization относится только к production/live-data контуру.

Проверяемые области:

- SPOT pipeline;
- instrument radar;
- candidate score;
- directional RS tie-break;
- event-risk gate;
- readiness;
- trigger activation;
- futures mapping boundary;
- expiry safety;
- historical/production parity.

---

## 12. ВАЛИДИРОВАННЫЕ CHECKPOINTS

### SPOT-first ranking

- Futures metrics исключены из SPOT score/ranking.
- Production candidate проходит через канонический `FuturesTradeCandidateService.build_candidate()` до futures mapping.
- Directional RS tie-break синхронизирован production/historical.

### Readiness boundary

- Futures mapping выполняется только после SPOT readiness.
- `WATCH + trigger` не является достаточным условием mapping.
- Direction mismatch блокирует mapping.
- Контракты с ≤3 днями до expiry исключаются.

### Trigger activation

27.08.2026 исправлено различие между `trigger level` и `trigger active`:

- LONG активируется при `price >= trigger`;
- SHORT активируется при `price <= trigger`;
- `READY` требует активного направленного trigger;
- UI разделяет trigger level, trigger state и SPOT READY;
- futures не участвует в trigger decision.

### Offline regression isolation

27.08.2026 unit-тесты instrument radar изолированы от BCS authorization: deterministic tests не требуют live refresh token.

---

## 13. CURRENT CHECKPOINT — ACTIVE SPOT TRIGGER BEFORE FUTURES MAPPING

**Дата:** 27.08.2026  
**Service:** `FuturesMorningRadarService 1.3`  
**Commit:** `e8bdf0a518d36247259bec523f0d6a550fddc41c`

Усилена production boundary между SPOT readiness и futures mapping.

### Изменение

Ранее `_spot_ready_for_mapping()` проверял наличие положительного `entry_trigger` и состояние `READY/CONFIRMED`, но не проверял, достигла ли текущая SPOT цена этого уровня.

Теперь mapping допускается только при фактической directional activation:

```text
LONG  → spot_price >= entry_trigger
SHORT → spot_price <= entry_trigger
```

Добавлен отдельный pure helper:

`FuturesMorningRadarService._spot_trigger_active()`

`_spot_ready_for_mapping()` использует его как обязательный gate.

### Regression coverage

`Program/test_futures_morning_radar_service.py` дополнен проверками:

- LONG active trigger;
- LONG unreached trigger;
- SHORT active trigger;
- SHORT unreached trigger;
- `READY + unreached trigger → no futures mapping`;
- `READY + active trigger → mapping allowed`;
- проверка отсутствия самого вызова mapping при unreached trigger.

### Инвариант

> **SPOT READY + trigger level без фактической activation не может запустить futures mapping.**

Это закрывает архитектурную цепочку:

`DIRECTION → SETUP → TRIGGER LEVEL → TRIGGER ACTIVE → READY → FUTURES MAPPING`

Futures остаётся `MAPPING ONLY`.

---

## 14. RELEASE / WORKFLOW RULE

После каждого законченного уровня проекта:

1. изменения делаются в GitHub `main`;
2. commit сохраняется в GitHub;
3. `main` синхронизируется;
4. `PROJECT_PASSPORT.md` обновляется;
5. проходят compile/regression checks;
6. пользователю выдаётся одна команда для локального `git pull` и reinstall/validation при необходимости.

**Канонический паспорт:** `Docs/PROJECT_PASSPORT.md`  
**Единственная рабочая ветка:** `main`
