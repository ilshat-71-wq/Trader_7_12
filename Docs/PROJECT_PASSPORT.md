# TRADER_7_12 PRO — PROJECT PASSPORT

**Дата актуализации:** 01.09.2026  
**Репозиторий:** `ilshat-71-wq/Trader_7_12`  
**Ветка:** `main`  
**Назначение:** read-only full-market opportunity scanner / помощник для самостоятельной intraday-торговли фьючерсами Московской биржи.

> Архитектор — ChatGPT, автор и владелец торговой идеи — пользователь. Сканер ищет, где сегодня есть деньги, активность, сила/слабость и сформированный сценарий. Он не торгует вместо пользователя.

---

## 1. ЦЕЛЬ ПРОЕКТА

Trader_7_12 ежедневно отсматривает максимально широкий доступный рынок и сначала определяет, **где прямо сейчас концентрируется денежный поток**, а затем направляет дорогой технический анализ именно туда.

```text
ALL AVAILABLE TQBR STOCKS
OIL / GOLD / GAS / FX
        ↓
SESSION MONEY / MONEY PER MINUTE / ACTIVITY / LIQUIDITY
        ↓
TOP ACTIVE TODAY
        ↓
SPOT DIRECTION / RS / SETUP / TRIGGER / STABILITY
        ↓
SPOT TRADE WATCHLIST
        ↓
USER CHOOSES THE FUTURE TO TRADE

MACRO OIL / GOLD / GAS / FX
        ↓
SEPARATE FUTURES_DIRECT WATCH
```

`opportunity_score` — рейтинг модели, **не вероятность прибыли**.

---

## 2. ГЛАВНОЕ АРХИТЕКТУРНОЕ ПРАВИЛО

### Equity path

**SPOT является единственным источником направления, денег/активности, RS, setup, trigger и readiness для equity trade radar. Futures — только mapping/reference после SPOT readiness.**

Фьючерс не подтверждает направление SPOT и не меняет RS, setup, readiness или ranking.

### Macro path

Если пригодный SPOT для OIL/GOLD/GAS/FX недоступен, используется явный `FUTURES_DIRECT`. Такой источник никогда не маскируется под SPOT и никогда не попадает в equity trade ranking.

```text
analysis_source = FUTURES_DIRECT
spot_data_status = UNAVAILABLE_PROXY_TO_FUTURES
relative_strength_status = UNAVAILABLE
selection_role = MACRO_WATCH
```

Синтетический SPOT и искусственный RS запрещены.

---

## 3. FULL-MARKET UNIVERSE

### Акции

Источник — `SpotUniverseService` → BCS dynamic SPOT metadata.

Канонический equity board:

```text
STOCK + TQBR
```

В live full-market режиме money-screen проходит **весь доступный канонический TQBR stock universe**, а не только IMOEX.

### Macro

`MarketTradingUniverseService` классифицирует динамические futures metadata. Контракты без пригодной даты экспирации и контракты с `days_to_expiry <= 3` исключаются.

---

## 4. MONEY-FIRST DISCOVERY

`Program/services/broad_market_money_scanner_service.py`.

Алгоритм:

1. загрузить весь TQBR universe;
2. для каждой акции получить текущий session money volume;
3. рассчитать `money_per_minute` и recent activity;
4. отсортировать по текущей денежной активности;
5. первые активные инструменты направить в deep SPOT analysis.

Ключевые поля:

```text
money_rank
spot_session_money
spot_money_per_minute
recent_money_volume
recent_money_per_minute
money_scan_status
spot_universe = ALL_TQBR_STOCKS
```

Полный money-screen не является ограничением universe. Ограничение deep-stage — это только экономия дорогих запросов.

---

## 5. TOP ACTIVE MONEY — ОТДЕЛЬНЫЙ СЛОЙ

`TOP ACTIVE MONEY — TQBR` является **discovery-информацией**, а не торговым сигналом.

Даже если ни одна акция ещё не прошла полный SPOT setup/readiness pipeline, UI обязан показывать лидеров текущей сессии по деньгам и темпу:

```text
MONEY RANK
SESSION ₽×V
₽×V/MIN
```

Это предотвращает ситуацию, когда отсутствие готового setup скрывает от пользователя, где фактически находится ликвидность рынка.

---

## 6. DEEP SPOT ANALYSIS

После money-first discovery активные акции проходят canonical pipeline:

```text
D TREND
↓
H1 CONTEXT
↓
RELATIVE STRENGTH
↓
M5 SETUP
↓
TRIGGER
↓
TWO-OBSERVATION STABILITY
↓
WAIT / WATCH / READY / CONFIRMED
↓
FUTURES MAPPING
```

Futures mapping появляется только после SPOT readiness/active trigger согласно canonical gate и является справочной привязкой, а не частью SPOT signal calculation.

---

## 7. RELATIVE STRENGTH

Benchmark для equity SPOT path:

```text
IMOEX2 / IRUS2
```

```text
RS = instrument_return - benchmark_return
```

Для `FUTURES_DIRECT` RS остаётся unavailable. Никакого синтетического RS нет.

---

## 8. MACRO DIRECT

Macro coverage работает независимо от equity SPOT path.

Используются текущие пригодные dated futures, daily radar при наличии, explicit intraday fallback, session money/activity, directional movement, setup quality и liquidity/expiry information.

Macro direct/proxy является **отдельным наблюдательным слоем**. Он не является equity SPOT signal и не может занять место SPOT-кандидата в основном рейтинге.

В UI macro показывается как `MACRO / FUTURES WATCH — ОТДЕЛЬНО`.

---

## 9. SIGNAL SAFETY

Главный invariant:

> Trigger level ≠ trigger activation.

```text
LONG  → price >= trigger
SHORT → price <= trigger
```

Live pipeline использует двухнаблюдательный stability gate.

`READY` и `CONFIRMED` — аналитические состояния, а не торговые команды.

---

## 10. FULL-MARKET RANKING

Приоритет пользовательского торгового радара:

```text
REAL SPOT EQUITY CANDIDATES ONLY
        ↓
signal state / opportunity / activity / money
        ↓
USER CHOOSES CORRESPONDING FUTURES CONTRACT
```

Macro futures не смешиваются с equity ranking. Даже высокий proxy-score macro не может стать `#1` SPOT-кандидатом.

Одновременно money-first leaderboard остаётся доступным отдельно и всегда показывает текущих лидеров TQBR.

---

## 11. FULL MARKET PIPELINE

`Program/services/full_market_pipeline_service.py` — публичный wrapper.

```text
BroadMarketMoneyScannerService
        ↓
ALL TQBR MONEY SCREEN
        ↓
TOP ACTIVE MONEY
        ↓
TOP ACTIVE → DEEP SPOT
        ↓
DIRECTION → RS → SETUP → TRIGGER → READINESS
        ↓
SPOT TRADE RADAR
        ↓
FUTURES MAPPING / USER SELECTION

PLUS

MacroMarketRadarService
        ↓
OIL / GOLD / GAS / FX
        ↓
FUTURES_DIRECT
        ↓
SEPARATE MACRO WATCH
```

Публичный вызов:

```python
FullMarketPipelineService().scan(limit=3)
```

`scan()` возвращает **только SPOT/equity trade-radar candidates**. Macro доступен через diagnostics/UI watch layer.

Scanner read-only.

---

## 12. LIVE OPERATING WINDOW

Основное окно поиска пользователя:

```text
07:00 → 13:00 MSK
```

Рекомендуемый cadence:

```text
07:00  07:30  08:00  08:30
09:00  09:30  10:00  10:30
11:00  11:30  12:00  12:30
13:00 контрольная точка
```

Это окно поиска и наблюдения, а не приказ открыть/закрыть сделку.

---

## 13. UI / OUTPUT

UI обязан различать три уровня:

### Discovery

```text
TOP ACTIVE MONEY — TQBR
RANK
TICKER
SESSION ₽×V
₽×V/MIN
```

### Trade radar

```text
SPOT / TQBR
DIRECTION
RS
SETUP
TRIGGER
READINESS
```

### Macro watch

```text
MACRO / FUTURES WATCH — ОТДЕЛЬНО
FUTURES_DIRECT
MACRO GROUP
CONTRACT
SESSION MONEY
DIRECTION
SETUP
TRIGGER
```

Macro proxy не должен выглядеть как подтверждённый SPOT trade signal.

Фьючерс для equity-кандидата показывается только как справочное сопоставление после SPOT readiness; пользователь самостоятельно выбирает контракт.

---

## 14. BCS AUTHORIZATION

BCS access token живёт только в процессе.

Refresh token хранится локально вне Git:

```text
~/.config/Trader_7_12/bcs_refresh_token
chmod 600
```

Секреты в Git запрещены.

---

## 15. TESTS / REGRESSION

Тесты deterministic и не требуют реального BCS token.

Последний подтверждённый локальный checkpoint пользователя:

```text
182 passed
compile=0
```

После изменения разделения SPOT/MACRO необходимо повторно подтвердить этот checkpoint локальным полным прогоном перед следующим live-тестом.

Критические regression areas:

- canonical TQBR board selection;
- ALL-TQBR money-first screening;
- recent money activity metrics;
- SPOT universe independent from futures mapping;
- `scan()` returns only SPOT equity trade candidates;
- macro futures excluded from equity ranking;
- macro watch remains visible separately;
- futures mapping deferred until SPOT readiness;
- macro universe groups;
- expiry safety;
- macro intraday fallback;
- persistent BCS refresh token;
- no synthetic macro RS;
- signal stability / anti-churn;
- full-market money-first dependency wiring;
- visible TOP ACTIVE MONEY even when no SPOT trade candidate is ready.

---

## 16. REPOSITORY HYGIENE

Разработка ведётся только в:

```text
main
```

Лишние рабочие ветки не создаются.

`Docs/PROJECT_PASSPORT.md` — единственный проектный MD-файл и архитектурный checkpoint.

---

## 17. CURRENT ARCHITECTURAL GAPS

### P1 — Broad-market speed

Money-first discovery сейчас делает session-money requests по полному TQBR universe. Следующее ускорение — использовать BCS bulk/WebSocket market-data возможности, не меняя математическую семантику ranking.

### P1 — Macro analytical parity

Усилить отдельный macro-specific D/H1/M5 trend profile там, где доступна futures history.

### P1 — Macro event risk

Добавить отдельный direct-macro event-risk contract.

### P2 — Validated expectancy

Закончить historical expectancy engine после накопления достаточной статистики.

### P2 — Data-quality observability

Для каждого market group явно хранить:

```text
AVAILABLE
UNAVAILABLE
PROXY
NO_TRADES
NO_DAILY_HISTORY
NO_ORDER_BOOK
```

---

## 18. OPERATING SAFETY

Проект находится в стадии контролируемого пользовательского тестирования.

Сканер:

- не гарантирует прибыль;
- не гарантирует доходность;
- не открывает сделки;
- не рассчитывает position sizing;
- не принимает торговое решение за пользователя;
- не подменяет самостоятельный анализ и контроль риска.

---

## 19. CHECKPOINT 01.09.2026

```text
Repository                     ilshat-71-wq/Trader_7_12
Branch                         main
Repository branches            main only
Project MD                      Docs/PROJECT_PASSPORT.md only
BCS persistent auth             implemented
Dynamic TQBR universe           implemented
ALL-TQBR money-first screen     implemented
Recent money activity           implemented
TOP ACTIVE MONEY UI             implemented
Deep active-stock analysis      implemented
SPOT-first direction/RS/setup   implemented
Equity SPOT-only ranking        enforced
Deferred futures mapping        enforced
User chooses futures             enforced
OIL coverage                    implemented
GOLD coverage                   implemented
GAS coverage                    implemented
USD/RUB coverage                implemented
EUR/CNY/KZT FX coverage         implemented
Macro FUTURES_DIRECT             implemented
Macro watch separation          enforced
No synthetic macro RS            enforced
Read-only scanner               enforced
Order execution                 absent
Primary discovery window        07:00-13:00 MSK
Live cadence                    30 minutes
User trade decision             external to scanner
```

**Главная цель текущей версии:** каждый торговый день сначала определить, **где прямо сейчас находятся деньги и высокая активность**, затем направить технический анализ именно туда. Основной торговый радар показывает только SPOT/TQBR-сценарии. После валидного SPOT-сценария пользователь самостоятельно выбирает соответствующий фьючерс. OIL/GOLD/GAS/FX остаются отдельным macro/futures наблюдательным слоем и не создают ложного SPOT-сигнала.
