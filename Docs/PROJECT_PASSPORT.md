# TRADER_7_12 PRO — PROJECT PASSPORT

**Дата актуализации:** 01.09.2026  
**Репозиторий:** `ilshat-71-wq/Trader_7_12`  
**Ветка:** `main`  
**Назначение:** read-only full-market opportunity scanner / помощник для самостоятельной intraday-торговли фьючерсами Московской биржи.

> Архитектор — ChatGPT, автор и владелец торговой идеи — пользователь. Сканер ищет, **где сегодня есть деньги, активность, сила/слабость и сформированный сценарий**, но не торгует вместо пользователя. Исполнение ордеров, position sizing и торговые SL/TP отсутствуют.

---

## 1. ЦЕЛЬ ПРОЕКТА

Trader_7_12 должен ежедневно отсматривать максимально широкий доступный рынок и выделять инструменты, в которых **сегодня реально концентрируется денежный поток**.

Целевая схема:

```text
ВСЕ ДОСТУПНЫЕ TQBR АКЦИИ
OIL
GOLD
GAS
USD/RUB
EUR/RUB
CNY/RUB
KZT/RUB
        ↓
SESSION MONEY / MONEY PER MINUTE / ACTIVITY / LIQUIDITY
        ↓
TOP ACTIVE TODAY
        ↓
TREND / RS WHEN VALID
        ↓
H1 CONTEXT → M5 SETUP → TRIGGER → STABILITY
        ↓
OPPORTUNITY RANKING
        ↓
TOP WATCHLIST
        ↓
USER CHOOSES THE FUTURE TO TRADE
```

`opportunity_score` — рейтинг модели, **не вероятность прибыли**.

---

## 2. ГЛАВНОЕ АРХИТЕКТУРНОЕ ПРАВИЛО

### Для акций

**SPOT является источником анализа. Futures — только mapping/reference.**

Фьючерс не подтверждает направление SPOT, не меняет RS, setup, readiness и ranking.

### Для OIL/GOLD/GAS/FX

Если BCS не даёт пригодного SPOT-источника, применяется явный `FUTURES_DIRECT`.

Это означает:

```text
analysis_source = FUTURES_DIRECT
spot_data_status = UNAVAILABLE_PROXY_TO_FUTURES
mapping_method = FUTURES_DIRECT
```

Синтетический SPOT и искусственный RS запрещены.

---

## 3. FULL-MARKET UNIVERSE

### Акции

Источник — `SpotUniverseService` → BCS dynamic SPOT metadata.

Канонический equity board:

```text
STOCK + TQBR + MOEX
```

Сканер больше **не ограничивается IMOEX 46 бумагами**. В live full-market режиме money-screen проходит весь доступный канонический TQBR stock universe.

### Macro

`MarketTradingUniverseService` классифицирует динамические futures metadata.

Контракты без пригодной даты экспирации и контракты с `days_to_expiry <= 3` исключаются.

Никакой фиксированный список одного тикера не является источником истины: BCS metadata остаётся динамическим источником universe.

---

## 4. MONEY-FIRST DISCOVERY

`Program/services/broad_market_money_scanner_service.py`.

В live режиме:

1. загружается весь канонический TQBR stock universe;
2. для **каждой** акции рассчитывается текущий session money volume;
3. рассчитывается `money_per_minute`;
4. все акции сортируются по фактической денежной активности текущей сессии;
5. только наиболее активные получают дорогой deep analysis.

По умолчанию в deep stage передаются первые 25 инструментов money ranking. Это **не ограничение universe** — это ограничение дорогой аналитической стадии после полного money-screen.

Ключевые поля:

```text
money_rank
spot_session_money
spot_money_per_minute
money_scan_status
spot_universe = ALL_TQBR_STOCKS
```

---

## 5. DEEP SPOT ANALYSIS

После money-first discovery наиболее активные акции проходят существующий canonical pipeline:

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
STABILITY
↓
WAIT / WATCH / READY / CONFIRMED
↓
FUTURES MAPPING
```

Futures mapping появляется только после SPOT readiness/active trigger согласно canonical gate.

---

## 6. MONEY / ACTIVITY / LIQUIDITY

Используются:

- current-session money volume;
- money per minute;
- average daily money, когда доступен deep radar;
- normalized session activity ratio;
- turnover;
- trade count;
- depth;
- spread;
- expiry safety;
- futures liquidity selector.

Отсутствие одного endpoint не должно превращаться в выдуманные данные.

---

## 7. RELATIVE STRENGTH

Benchmark для SPOT/equity path:

```text
IMOEX2 / IRUS2
```

```text
RS = instrument_return - benchmark_return
```

Для `FUTURES_DIRECT`:

```text
relative_strength_status = UNAVAILABLE
relative_strength_benchmark = NOT_APPLICABLE_FOR_MACRO_DIRECT
```

Синтетический RS запрещён.

---

## 8. MACRO DIRECT

Macro coverage работает независимо от equity SPOT path.

Для каждой macro group выбираются текущие пригодные dated futures. Затем используются daily radar, explicit intraday fallback, current money/activity, directional movement, setup quality и liquidity/expiry information.

Нет trades / нет direction → кандидат не создаётся.

---

## 9. SETUP / TRIGGER / ANTI-CHURN

Главный invariant:

> Trigger level ≠ trigger activation.

```text
LONG  → price >= trigger
SHORT → price <= trigger
```

Live pipeline использует двухнаблюдательный stability gate.

`READY` и `CONFIRMED` — аналитические состояния, а не торговые команды.

---

## 10. RANKING

Итоговый full-market ranking объединяет:

```text
SPOT candidates + MACRO FUTURES_DIRECT candidates
        ↓
SESSION RANK
        ↓
OPPORTUNITY RANK
```

Для equities дополнительным discovery factor является фактический `money_rank` по всему TQBR universe.

TOP не заполняется искусственно: отсутствие качественных кандидатов допустимо.

---

## 11. FULL MARKET PIPELINE

`Program/services/full_market_pipeline_service.py` — публичный full-market wrapper.

```text
BroadMarketMoneyScannerService
        ↓
ALL TQBR MONEY SCREEN
        ↓
TOP ACTIVE STOCKS
        ↓
TwoPhaseFuturesMorningRadarService
        ↓
DEEP SPOT ANALYSIS
        ↓
FUTURES MAPPING AFTER READINESS

PLUS

MacroMarketRadarService
        ↓
OIL / GOLD / GAS / USDRUB / FX
        ↓
FUTURES_DIRECT

        ↓
UNIFIED RANKING
        ↓
TOP WATCHLIST
```

Публичный вызов:

```python
FullMarketPipelineService().scan(limit=3)
```

Scanner read-only.

---

## 12. LIVE OPERATING WINDOW

Основное окно поиска активных инструментов пользователя:

```text
07:00 → 13:00 MSK
```

Рекомендуемый live cadence:

```text
07:00
07:30
08:00
08:30
09:00
09:30
10:00
10:30
11:00
11:30
12:00
12:30
13:00 контрольная точка
```

Это **окно поиска и наблюдения**, а не приказ открыть или закрыть сделку. После 13:00 рынок не считается недоступным; просто приоритет нового поиска переносится на следующий торговый цикл.

Аукцион открытия не должен смешиваться с нормальным session-money потоком.

---

## 13. UI / OUTPUT

UI должен показывать не только «лучший сигнал», а происхождение данных.

Для equity:

```text
ALL_TQBR_STOCKS
MONEY RANK
SESSION MONEY
MONEY/MIN
DIRECTION
RS
SETUP
TRIGGER
READINESS
FUTURES MAPPING
```

Для macro:

```text
FUTURES_DIRECT
MACRO GROUP
CONTRACT
SESSION MONEY
DIRECTION
SETUP
TRIGGER
```

Diagnostics:

```text
ALL_TQBR
MONEY_SCREENED
DEEP
MACRO
TOTAL
SELECTED
READY
CONFIRMED
WATCH
WAIT
MACRO_SOURCES
```

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

Критические regression areas:

- canonical TQBR board selection;
- SPOT universe independent from futures mapping;
- futures mapping deferred until SPOT readiness;
- macro universe groups;
- expiry safety;
- live macro intraday fallback;
- persistent BCS refresh token;
- full-market macro output;
- no synthetic RS for macro;
- signal stability / anti-churn;
- full-market money-first dependency wiring.

---

## 16. REPOSITORY HYGIENE

Разработка ведётся только в:

```text
main
```

Лишние рабочие ветки не создаются.

`Docs/PROJECT_PASSPORT.md` — единственный проектный MD-файл и архитектурный checkpoint.

Не создавать дополнительные MD-файлы без отдельной необходимости.

---

## 17. CURRENT ARCHITECTURAL GAPS

### P1 — Broad-market speed

Money-first discovery сейчас делает session-money requests по полному TQBR universe. Следующее ускорение — использовать BCS bulk/WebSocket market-data возможности, не меняя математическую семантику money ranking.

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
Repository                    ilshat-71-wq/Trader_7_12
Branch                        main
Repository branches           main only
Project MD                     Docs/PROJECT_PASSPORT.md only
BCS persistent auth            implemented
Dynamic TQBR universe          implemented
ALL-TQBR money-first screen    implemented
Deep active-stock analysis     implemented
OIL coverage                   implemented
GOLD coverage                  implemented
GAS coverage                   implemented
USD/RUB coverage               implemented
EUR/CNY/KZT FX coverage       implemented
Macro FUTURES_DIRECT           implemented
No synthetic macro RS          enforced
Read-only scanner              enforced
Order execution                absent
Primary discovery window       07:00-13:00 MSK
Live cadence                   30 minutes
User trade decision            external to scanner
```

**Главная цель текущей версии:** не искать несколько заранее известных тикеров, а каждый торговый день сначала определить, **где в реальном рынке сегодня находятся большие деньги и высокая активность**, затем направлять дорогой технический анализ именно туда и только после готового SPOT-сценария выбирать соответствующий фьючерс.
