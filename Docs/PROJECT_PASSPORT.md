# TRADER_7_12 PRO — PROJECT PASSPORT

**Дата актуализации:** 30.08.2026  
**Репозиторий:** `ilshat-71-wq/Trader_7_12`  
**Ветка:** `main`  
**Текущий HEAD:** `d57862d`  
**Назначение:** read-only full-market opportunity scanner / помощник для самостоятельной intraday-торговли фьючерсами Московской биржи.

> Архитектор — ChatGPT, автор и владелец торговой идеи — пользователь. Главный принцип: сканер ищет **ГДЕ есть потенциальное преимущество**, а не торгует вместо пользователя. Исполнение ордеров, SL/TP и position sizing отсутствуют.

---

## 1. ЦЕЛЬ

Ежедневно выделять лучшие текущие возможности по всему доступному рынку:

```text
SPOT EQUITIES
OIL
GOLD
GAS
USDRUB
    ↓
MONEY / ACTIVITY / LIQUIDITY
    ↓
TREND
    ↓
RELATIVE STRENGTH WHEN VALID
    ↓
SETUP / TRIGGER / STABILITY
    ↓
OPPORTUNITY RANKING
    ↓
TOP WATCHLIST
    ↓
USER DECIDES WHETHER / WHICH FUTURE TO TRADE
```

`opportunity_score` — рейтинг модели, **не вероятность прибыли**.

---

## 2. SPOT-FIRST / MACRO-DIRECT BOUNDARY

Для обычного equity pipeline базовый актив — SPOT. Futures — только reference mapping и не подтверждают SPOT signal.

Для `USD000SMALL / CETS_FX`, а также для OIL/GOLD/GAS, BCS может не отдавать пригодные SPOT candles. Поэтому существует явный `FUTURES_DIRECT` coverage layer.

`FUTURES_DIRECT` означает:

- анализируется сам доступный фьючерсный контракт;
- `analysis_source = FUTURES_DIRECT`;
- `spot_data_status = UNAVAILABLE_PROXY_TO_FUTURES`;
- `mapping_method = FUTURES_DIRECT`;
- синтетический SPOT не создаётся;
- RS относительно IMOEX2/IRUS2 не придумывается.

Это **coverage fallback**, а не ложное утверждение о полноценном SPOT-анализе.

---

## 3. FULL-MARKET UNIVERSE

`Program/services/market_trading_universe_service.py` определяет группы:

```text
MOEX_STOCK
OIL
GOLD
GAS
USDRUB
```

Текущий macro universe строится из BCS futures metadata. Для каждой группы выбираются ближайшие допустимые контракты, а контракты с `days_to_expiry <= 3` исключаются.

Подтверждено реальным BCS screening 30.08.2026: доступны фьючерсные сделки по `BRV6`, `GDU6`, `NGU6`, `FFU6`; order-book для `GLU6` вернул HTTP 404, что трактуется как отсутствие конкретного источника, а не как отсутствие рынка.

---

## 4. DAILY TREND

`Program/services/daily_trend_profile_service.py` — deterministic network-free слой завершённых D-свечей.

Анализируются окна 2 / 3 / 4 завершённых дней:

- direction: `LONG / SHORT / NEUTRAL`;
- state: `PERSISTENT / CONSISTENT / WEAK / MIXED`;
- price change;
- directional days;
- consistency.

Для aggregate LONG/SHORT требуется подтверждение минимум двумя доступными окнами.

Для обычного SPOT pipeline это канонический слой. Для `FUTURES_DIRECT` он используется, когда доступна пригодная daily history; отсутствие daily history не должно блокировать live macro coverage.

---

## 5. MORNING RADAR

`morning_radar_service.py` и `instrument_morning_radar_service.py` обеспечивают SPOT/equity path:

- завершённые D-свечи;
- daily trend;
- average daily money;
- preliminary radar score;
- setup preparation.

Legacy `TREND_DAYS = 3` сохраняется только для обратной совместимости.

---

## 6. MONEY / ACTIVITY / LIQUIDITY

Используются:

- session money volume;
- average daily money;
- money per minute;
- activity ratio;
- futures contract selector;
- liquidity score;
- spread score;
- expiry score;
- turnover / trade count / depth, когда BCS их предоставляет.

Для macro proxy эти показатели относятся к самому futures contract и не маскируются под SPOT.

---

## 7. RELATIVE STRENGTH

Benchmark: `IMOEX2 / IRUS2`.

```text
RS = instrument_return - benchmark_return
```

SPOT/equity path использует RS как directional factor.

Для macro direct:

```text
relative_strength_status = UNAVAILABLE
relative_strength_benchmark = NOT_APPLICABLE_FOR_MACRO_DIRECT
```

Синтетический RS запрещён.

---

## 8. SETUP / READINESS

Canonical SPOT model:

```text
H1 context
   ↓
M5 setup
   ↓
trigger
   ↓
stability
   ↓
WAIT → WATCH → ARMED → READY → CONFIRMED
```

LONG: impulse → first pullback → continuation.  
SHORT: impulse → first rebound → continuation.

`READY/CONFIRMED` — аналитические состояния, не торговые команды.

Macro direct может использовать тот же setup service на proxy futures, но результат всегда остаётся `FUTURES_DIRECT`.

---

## 9. TRIGGER / ANTI-CHURN

Главный invariant:

> Trigger level ≠ trigger activation.

```text
LONG  → price >= trigger
SHORT → price <= trigger
```

`MorningTradingPipelineService` использует двухнаблюдательный stability gate.

Для macro direct trigger, если сформирован, относится к proxy futures и не является SPOT confirmation.

---

## 10. EVENT RISK

Для canonical SPOT path `moex_event_risk` является eligibility gate.

Для macro direct отдельный полноценный macro event-risk gate остаётся следующим архитектурным усилением. Нельзя скрывать этот gap под SPOT event-risk semantics.

---

## 11. RANKING

SPOT:

```text
candidate_score
→ session_rank_score
→ opportunity_score
→ signal priority
```

Macro direct использует отдельный bounded score на основе доступных:

- activity;
- money;
- directional movement;
- setup quality.

Macro direct **не получает искусственный RS**.

TOP не заполняется искусственно: отсутствие качественных кандидатов допустимо.

---

## 12. LIVE MACRO INTRADAY FALLBACK — НОВОЕ

30.08.2026 реальный weekend screening показал архитектурный дефект: macro futures реально торговались и BCS возвращал trades, но `MacroMarketRadarService` пытался вызвать неподходящий метод на верхнем radar object и затем отбрасывал macro candidates.

Исправлено в `macro_market_radar_service.py`:

1. Сначала используется canonical `analyze()` внутреннего instrument radar.
2. Если daily radar не даёт direction, запускается явный `_direct_trade_snapshot()`.
3. Fallback использует BCS `last-trades` за текущие 30 минут.
4. Направление определяется только по фактическому изменению first → last trade:
   - рост → LONG;
   - падение → SHORT;
   - без движения → кандидат не создаётся.
5. Fallback маркируется:

```text
macro_analysis_status = INTRADAY_PROXY
analysis_source = FUTURES_DIRECT
spot_data_status = UNAVAILABLE_PROXY_TO_FUTURES
```

6. Если BCS не даёт quantity/volume, это не подменяется выдуманным оборотом.
7. Полученный proxy money используется только как дополнительный direct-macro activity input.

Это исправление предназначено именно для live/weekend futures sessions.

---

## 13. FULL MARKET PIPELINE

`Program/services/full_market_pipeline_service.py`:

```text
MorningTradingPipelineService
          │
          ├── canonical SPOT/equity path
          │
          └── MacroMarketRadarService
                  ├── OIL
                  ├── GOLD
                  ├── GAS
                  └── USDRUB
          │
          ↓
      unified ranking
          ↓
      TOP watchlist
```

Публичный метод полного сканера:

```python
FullMarketPipelineService().scan(limit=3)
```

Метода `run()` у этого класса нет и добавлять фиктивный API не требуется.

---

## 14. OUTPUT CONTRACT

Full-market output явно показывает:

- `analysis_source`;
- `macro_analysis_status`;
- `spot_data_status`;
- `spot_group / market_group`;
- `futures_ticker`;
- `futures_expiry`;
- direction;
- signal state;
- setup;
- trigger;
- opportunity score.

Диагностика содержит:

```text
SPOT candidates
MACRO candidates
TOTAL candidates
SELECTED
READY
CONFIRMED
WATCH
WAIT
MACRO_SOURCES
```

Вывод не утверждает, что весь scanner является только SPOT-only pipeline.

---

## 15. FUTURES MAPPING

Canonical SPOT:

- futures mapping появляется только после SPOT readiness;
- futures не подтверждают SPOT signal;
- expiry safety обязателен.

Macro direct:

- futures contract сам является анализируемым proxy;
- это не mapping к подтверждённому SPOT signal.

---

## 16. HISTORICAL REPLAY / EXPECTANCY

Historical replay остаётся READ ONLY / NO ORDERS.

Production mathematical-expectancy engine с достаточной validated sample history пока **TODO**.

Нельзя отображать expectancy как доказанную вероятность прибыли до достаточной статистики.

---

## 17. LONG / SHORT BALANCE

При отсутствии качественного источника значение остаётся `UNAVAILABLE`.

Синтетическая оценка LONG/SHORT balance запрещена.

---

## 18. TESTS / REGRESSION

Тесты deterministic и не требуют BCS token.

До macro live-fallback исправления на `main` было подтверждено:

```text
171 passed
compileall = 0
```

После добавления двух macro fallback regression tests ожидаемый полный suite — **173 tests**. Это должно быть подтверждено локальным запуском после `git pull`.

Новые regression cases:

- macro universe: четыре группы;
- expiry safety;
- explicit `FUTURES_DIRECT` marking;
- intraday proxy LONG direction;
- insufficient trades → no proxy candidate.

CI workflow `.github/workflows/spot-first-validation.yml` выполняет `compileall` и `pytest -q Program`.

---

## 19. REPOSITORY HYGIENE

Одна рабочая ветка:

```text
main
```

Без лишних рабочих веток для текущей разработки.

`PROJECT_PASSPORT.md` — единственный проектный MD-паспорт и источник архитектурного checkpoint.

BCS refresh token не хранится в Git; используется локальная environment variable `BCS_REFRESH_TOKEN`.

---

## 20. RC APP / UI

`Program/watchlist_ui.py` и установленный RC `.app` являются интерфейсным слоем.

`.app` не должен содержать отдельную копию Python production проекта.

UI не является источником торговой логики: canonical services остаются в `Program/services`.

---

## 21. ARCHITECTURAL GAPS / NEXT STEPS

### P1 — Macro analytical parity

Сделать полноценный macro-specific trend profile 2/3/4-day там, где доступна futures history, не выдавая его за SPOT.

### P1 — Macro event risk

Добавить отдельный direct-macro event-risk contract.

### P1 — Macro setup quality

Усилить proxy futures H1/M5 setup так, чтобы `WAIT/WATCH/READY/CONFIRMED` имели ту же строгость, но с macro-specific semantics.

### P2 — Validated expectancy

Закончить historical expectancy engine после накопления достаточной статистики.

### P2 — LONG/SHORT balance

Подключать только при появлении достоверного своевременного источника.

### P3 — Data-quality observability

Для каждого market group хранить причину:

```text
AVAILABLE
UNAVAILABLE
PROXY
NO_TRADES
NO_DAILY_HISTORY
NO_ORDER_BOOK
```

Отсутствие одного endpoint не должно молча превращаться в `NO_CANDIDATE`.

---

## 22. TRADING SAFETY / OPERATING RULE

Проект находится в стадии **контролируемого пользовательского тестирования**, а не доказанной прибыльности.

Сканер:

- не гарантирует ежедневную прибыль;
- не гарантирует доходность;
- не открывает сделки;
- не рассчитывает position sizing;
- не назначает SL/TP как торговое решение пользователя;
- не подменяет самостоятельное решение владельца проекта.

Целевая доходность пользователя не является параметром scanner engine.

---

## 23. CURRENT CHECKPOINT

На 30.08.2026 установлено:

```text
BCS authorization              OK
Full-market universe           OK
OIL futures data               OK
GOLD futures data              OK (order-book may be unavailable per contract)
GAS futures data               OK
USDRUB futures metadata        OK
USD000SMALL direct candles     UNAVAILABLE in observed BCS endpoint
FUTURES_DIRECT fallback        IMPLEMENTED
Weekend intraday fallback      IMPLEMENTED
Full-market scan API           scan()
Orders / execution             ABSENT
```

Последний исправляющий commit:

```text
d57862d  Add regression coverage for macro intraday fallback
```

После синхронизации локального `main` обязательный контроль:

```bash
cd ~/Documents/Trader_7_12
git pull --ff-only origin main
python3 -m compileall -q Program
PYTHONPATH=Program python3 -m pytest -q Program
git status --short --branch
```

**Архитектурный принцип:** сначала корректность и прозрачность данных, затем ranking; coverage не должен достигаться ценой скрытой подмены SPOT данными futures.
