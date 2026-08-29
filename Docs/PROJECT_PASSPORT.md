# TRADER_7_12 PRO — PROJECT PASSPORT

**Дата актуализации:** 30.08.2026  
**Репозиторий:** `ilshat-71-wq/Trader_7_12`  
**Ветка:** `main`  
**Текущий HEAD:** `e973948`  
**Назначение:** read-only SPOT-first opportunity scanner / помощник для самостоятельной intraday-торговли фьючерсами Московской биржи.

> Главный принцип: сканер ищет **ГДЕ есть потенциальное преимущество**, а не торгует вместо пользователя. Пользователь самостоятельно выбирает конкретный фьючерс, вход, размер позиции и риск. Исполнение ордеров, SL/TP и position sizing отсутствуют.

---

## 1. ЦЕЛЬ ПОМОЩНИКА

Ежедневно выделять **TOP-2/3 базовых SPOT-инструмента**, где одновременно наблюдаются:

- устойчивый дневной тренд;
- денежная активность, объём и оборот;
- достаточная ликвидность;
- относительная сила/слабость относительно рынка;
- направленный money flow;
- LONG/SHORT balance, только если есть достоверный источник;
- качественный intraday setup;
- подтверждённый trigger;
- положительное историческое математическое ожидание после накопления достаточной статистики.

Целевой сценарий:

```text
SPOT BASE ASSET
      ↓
MONEY / VOLUME / TURNOVER
      ↓
DAILY TREND 2 / 3 / 4 DAYS
      ↓
LIQUIDITY / ACTIVITY
      ↓
RELATIVE STRENGTH vs IMOEX2 / IRUS2
      ↓
LONG / SHORT BALANCE WHEN DATA IS AVAILABLE
      ↓
H1 STRUCTURE + M5 SETUP
      ↓
TRIGGER / STABILITY
      ↓
MATHEMATICAL EXPECTATION — AFTER VALIDATED HISTORY
      ↓
TOP 2–3 SPOT OPPORTUNITIES
      ↓
FUTURES MAPPING — REFERENCE ONLY
      ↓
USER DECIDES WHETHER / WHICH FUTURE TO TRADE
```

`opportunity_score` — рейтинг модели, **не вероятность прибыли**.

---

## 2. SPOT-FIRST / FUTURES BOUNDARY

Для обычного equity-пути фьючерс не определяет direction, daily trend, relative strength, SPOT eligibility, setup, trigger, readiness или SPOT ranking.

Для `SIU6` и других валютных контрактов исходная архитектурная цель — анализировать базовый актив **USD/RUB SPOT**, а фьючерс использовать только как способ реализации выбранного пользователем сценария.

**Текущее техническое состояние macro-пути:** BCS в текущем доступном universe надёжно возвращает фьючерсные контракты, включая `Si*`, `USDRUBF`, `BR*`, `GD*`, `NG*`, но отдельный SPOT `USD000SMALL/CETS_FX` в текущих проверках не возвращает свечи. Поэтому для OIL/GOLD/GAS/USDRUB добавлен явный `FUTURES_DIRECT` fallback. Он не скрывается под видом SPOT: результат маркируется `FUTURES_DIRECT`, `spot_data_status=UNAVAILABLE_PROXY_TO_FUTURES`, а анализируемый инструмент — сам доступный фьючерсный контракт.

**Важно:** `FUTURES_DIRECT` — временный/консервативный coverage layer, а не отмена SPOT-first архитектуры. Он не должен считаться эквивалентом полноценного SPOT pipeline.

---

## 3. DAILY TREND — КАНОНИЧЕСКИЙ СЛОЙ

`Program/services/daily_trend_profile_service.py` — deterministic network-free анализ завершённых дневных свечей.

**Version: 1.1**

Анализируются отдельные окна последних **2, 3 и 4 завершённых D-свечей**.

Для каждого окна:

- `direction`: `LONG / SHORT / NEUTRAL`;
- `state`: `PERSISTENT / CONSISTENT / WEAK / MIXED`;
- изменение цены;
- положительные и отрицательные дневные переходы;
- directional days;
- `consistency_percent`.

Aggregate direction является консервативным: одна короткая импульсная структура не должна переопределять более широкую картину. Для aggregate LONG/SHORT требуется подтверждение минимум двумя доступными окнами.

Принцип:

```text
2 дня ↑ → ранний фактор
3 дня ↑ → подтверждение устойчивости
4 дня ↑ → дополнительное подтверждение продолжения

2/3/4 дня ↓ → аналогично для SHORT
```

Один резкий день не считается устойчивым трендом автоматически.

**Реализация:** сервис и regression coverage существуют и проходят тесты. Однако в текущем `FUTURES_DIRECT` macro fallback этот канонический 2/3/4-day profile ещё не является обязательным источником macro ranking; macro path пока использует расчёт базового radar на выбранном фьючерсном контракте.

---

## 4. MORNING RADAR

`Program/services/morning_radar_service.py` остаётся источником завершённых D-свечей, daily direction, daily change, average daily money и money activity.

Legacy `TREND_DAYS = 3` сохраняется для обратной совместимости. `DailyTrendProfileService` является дополнительным каноническим аналитическим слоем 2/3/4 дня и подготовлен для усиления финального SPOT ranking.

---

## 5. MONEY / ACTIVITY / LIQUIDITY

Используются/предусмотрены:

- `price × volume`;
- session money volume;
- средний оборот завершённых дней;
- money per minute;
- activity ratio относительно собственной нормы;
- liquidity filters.

Абсолютный оборот сам по себе не является сигналом. Важна концентрация текущих денег, относительная активность, ликвидность и качество движения.

**Статус:** для основного SPOT/equity pipeline слой реализован. Для macro `FUTURES_DIRECT` есть session money/activity и contract selection/liquidity данные, но они относятся к proxy-фьючерсу, а не к недоступному SPOT underlying.

---

## 6. RELATIVE STRENGTH

Benchmark: `IMOEX2 / IRUS2`.

`relative_strength = instrument_return - benchmark_return`.

- `STRONGER`: RS ≥ +0.20 п.п.;
- `WEAKER`: RS ≤ −0.20 п.п.;
- `NEUTRAL`: промежуточная зона;
- `RS_UNAVAILABLE`: обязательные данные отсутствуют.

LONG должен согласовываться с `STRONGER`, SHORT — с `WEAKER`. Синтетический RS запрещён.

**Статус:** для обычного SPOT/equity candidate path RS является обязательным eligibility/ranking factor. Для `FUTURES_DIRECT` macro fallback RS явно `UNAVAILABLE`, benchmark `NOT_APPLICABLE_FOR_MACRO_DIRECT`; синтетический RS не создаётся. Следовательно, macro fallback не достигает полноты обычного SPOT ranking.

---

## 7. SETUP / READINESS

H1 задаёт контекст, M5 формирует сценарий.

LONG: `H1 up → impulse → first pullback → stabilization → continuation`  
SHORT: `H1 down → impulse → first rebound → stabilization → continuation`

Lifecycle:

```text
WAIT → WATCH → ARMED → READY → CONFIRMED
```

`INVALIDATED` — terminal state текущего lifecycle.

`READY/CONFIRMED` — аналитические состояния, не торговая команда.

**Статус:** lifecycle и SPOT setup/readiness реализованы в основном pipeline. Macro fallback умеет запускать setup analysis и общий двухнаблюдательный lifecycle, но анализируется proxy-фьючерс; это отдельный режим и не должен быть смешан с canonical SPOT signal.

---

## 8. TRIGGER / ANTI-CHURN

Главный invariant:

> Trigger level ≠ trigger activation.

```text
LONG  → spot_price >= entry_trigger
SHORT → spot_price <= entry_trigger
```

`MorningTradingPipelineService` использует двухнаблюдательный stability gate: первое active observation → `ARMED`, второе → `READY`.

Transient retreat не уничтожает lifecycle; explicit invalidation переводит его в `INVALIDATED`.

**Статус:** реализовано и покрыто regression tests для live/historical trigger contract. Для macro fallback trigger технически считается по proxy price и поэтому маркируется как macro direct, а не как подтверждение реального SPOT trigger.

---

## 9. SETUP QUALITY

`setup_quality_service.py` содержит bounded deterministic quality scoring. Quality отделена от detection/lifecycle и не должна самостоятельно превращать setup в READY/CONFIRMED.

**Статус:** реализовано. Macro fallback может использовать setup quality, но её источник — proxy-фьючерс.

---

## 10. RANKING

Основной SPOT ranking использует `candidate_score`, затем session-level `opportunity_score`.

TOP ограничен тремя кандидатами и не заполняется искусственно.

SPOT ranking не зависит от futures reference metrics. Directional RS является значимым directional factor / tie-break.

Daily 2/3/4-day profile предназначен для усиления ranking как **устойчивость направления**, а не как прогноз гарантированной доходности.

**Текущий macro ranking отличается:** `MacroMarketRadarService` имеет отдельный bounded score на основе proxy activity/money/movement/setup quality. Он сознательно не подменяет отсутствующий RS и не выдаёт macro proxy за полноценный SPOT candidate. Это рабочий coverage fallback, но не финальная архитектурная точка.

---

## 11. EVENT RISK

`moex_event_risk` является жёстким SPOT eligibility gate до candidate formation/mapping.

Сильный однодневный выброс без устойчивой структуры не должен автоматически становиться качественным кандидатом.

**Статус:** основной SPOT/equity candidate path использует event-risk gate. В текущем `FUTURES_DIRECT` macro fallback отдельный полноценный macro event-risk gate ещё не является обязательным фильтром. Это один из следующих архитектурных gaps.

---

## 12. HISTORICAL REPLAY / MATHEMATICAL EXPECTATION

Historical replay: **READ ONLY / NO ORDERS**.

Для будущего статистического слоя накапливаются:

- число наблюдений;
- win/loss;
- average adverse excursion;
- average favourable excursion;
- средний результат;
- payoff ratio;
- hit rate;
- expectancy;
- LONG/SHORT breakdown;
- liquidity/activity regimes;
- 2/3/4-day trend regimes.

До достаточной выборки expectancy не должна отображаться как доказанная вероятность прибыли.

**Фактический статус:** полноценный production-слой математического ожидания в текущем `main` ещё не завершён. Historical replay/ranking/regression infrastructure существует, но validated live/historical expectancy engine с накоплением достаточной статистики пока является TODO.

---

## 13. LONG / SHORT BALANCE

Фактор используется только при наличии достоверных и своевременных данных. При отсутствии качественного источника значение — `UNAVAILABLE`; синтетическая оценка запрещена.

**Фактический статус:** в текущем production pipeline отдельный подтверждённый источник LONG/SHORT balance не реализован. Значение должно оставаться `UNAVAILABLE`, а не заменяться расчётной догадкой. Это TODO при появлении качественного источника данных.

---

## 14. FUTURES MAPPING

Для обычного SPOT pipeline Futures — reference mapping выбранного SPOT-актива.

До `signal_state ∈ {READY, CONFIRMED}` futures mapping очищается из результата. После READY/CONFIRMED могут быть показаны ticker, expiry, days-to-expiry и направление SPOT-сценария.

Фьючерсы не подтверждают SPOT signal. Контракты с `days_to_expiry <= 3` исключаются из reference mapping.

**Macro exception:** для OIL/GOLD/GAS/USDRUB при отсутствии usable SPOT source действует `FUTURES_DIRECT`. В этом режиме контракт не является reference mapping к доступному SPOT signal: он сам является анализируемым proxy-инструментом. Поля `analysis_source`, `spot_data_status` и `mapping_method` явно это показывают.

---

## 15. FULL-MARKET COVERAGE

`Program/services/market_trading_universe_service.py` определяет целевую universe:

```text
MOEX_STOCK
OIL
GOLD
GAS
USDRUB
```

Поддерживаются группы фьючерсов, включая:

```text
OIL    → BR / BRM / CL / WT / WTI
GOLD   → GD / GOLD / GL / GOLDM / GLDRUBF
GAS    → NG / NGM / FF / TTF
USDRUB → SI / USDRUBF
```

`Program/services/macro_market_radar_service.py` и `full_market_pipeline_service.py` подключены к `Program/main.py`, поэтому текущий application path действительно содержит **акции + OIL/GOLD/GAS/USDRUB**.

**Но:** coverage ≠ полная аналитическая эквивалентность. Акции идут через canonical SPOT-first candidate path; macro markets при отсутствии usable SPOT source идут через явно маркированный `FUTURES_DIRECT` fallback. Это сознательно зафиксировано как промежуточное состояние, а не скрытый architectural shortcut.

---

## 16. TESTS / REGRESSION

Тесты deterministic и не требуют BCS token, сети или live market data.

Критический regression для daily trend проверяет, что:

```text
110 → 100 → 100   = SHORT для 3-дневного окна
100 → 110 → 100 → 100 = NEUTRAL для 4-дневного окна
```

Следовательно, единичный короткий импульс не создаёт aggregate SHORT.

**Текущий baseline на commit `e973948`: `171 passed`**.

Последняя добавленная regression coverage включает macro universe: четыре группы, expiry safety и явную маркировку `FUTURES_DIRECT`.

---

## 17. REPOSITORY HYGIENE

Удалены локальные/legacy артефакты:

- `*.bak`;
- `.DS_Store`;
- `.pytest_cache`;
- `__pycache__`;
- старые `Logs`;
- `Docs/historical_replay`;
- ранее удалённые legacy production files.

Production services не удаляются только потому, что они не импортируются напрямую из `main.py`: часть используется historical replay, diagnostics и regression tests.

---

## 18. INSTALLED `.APP`

Bundle:

`/Users/ilshatmac/Applications/Trader_7_12 Pro.app`

```text
CFBundleName:                Trader_7_12 Pro
Version:                     1.4
Bundle ID:                   com.trader712.pro
Architecture:                Mach-O x86_64
```

`.app` является тонким launcher bundle и использует канонический каталог:

`/Users/ilshatmac/Documents/Trader_7_12`

Launcher устанавливает `PYTHONPATH=$ROOT/Program` и запускает текущий `Program/main.py`.

BCS refresh token берётся из macOS Keychain и не хранится в Git, app bundle или plist.

`.app` не содержит отдельную копию Python проекта.

---

## 19. RC UI

`Program/watchlist_ui.py` содержит русский SPOT radar UI:

- `SPOT-РАДАР ВОЗМОЖНОСТЕЙ`;
- `ОЦЕНКА ВОЗМОЖНОСТИ`;
- `СИЛА СЦЕНАРИЯ`;
- `РЕКОМЕНДАЦИЯ`;
- `ДЕНЬГИ И АКТИВНОСТЬ`;
- `ОТНОСИТЕЛЬНАЯ СИЛА`;
- `СЕТАП И ТРИГГЕР`.

Оценка возможности — рейтинг модели, не статистическая вероятность.

---

## 20. ARCHITECTURAL AUDIT — 30.08.2026

Аудит выполнен непосредственно против текущего `main` на commit `e973948`, а не против старого состояния паспорта.

### Реализовано и подтверждено

- SPOT-first pipeline для equity universe;
- full-market universe с группами `MOEX_STOCK / OIL / GOLD / GAS / USDRUB`;
- macro direct fallback с явной маркировкой источника;
- deterministic daily trend 2/3/4 дня;
- money/activity/liquidity components;
- relative strength contract для SPOT path;
- H1/M5 setup infrastructure;
- trigger contract и двухнаблюдательный stability gate;
- setup quality scoring;
- event-risk gate для canonical SPOT candidate path;
- futures contract selection/mapping infrastructure;
- historical replay/regression infrastructure;
- read-only architecture без автоматических ордеров;
- application integration через `FullMarketPipelineService`;
- regression baseline: **171 passed**.

### Реализовано частично / архитектурно ограничено

1. **OIL/GOLD/GAS/USDRUB:** coverage уже подключён в приложение, но при недоступности SPOT source анализируется доступный dated futures proxy (`FUTURES_DIRECT`). Это не полноценный SPOT analysis.
2. **Macro daily trend:** macro fallback пока не требует канонического 2/3/4-day profile как обязательного ranking factor.
3. **Macro RS:** остаётся `UNAVAILABLE`, без синтетического RS.
4. **Macro event risk:** нет полноценного отдельного обязательного macro event-risk gate.
5. **Macro ranking:** используется отдельный bounded proxy score, а не полностью унифицированный SPOT candidate score.
6. **Macro trigger/setup:** lifecycle реализован, но уровни рассчитываются по proxy-фьючерсу.

### Не завершено / TODO

1. Найти и подключить стабильный исторический/live SPOT источник для `USD/RUB`, а также проверить эквивалентные корректные SPOT источники для OIL/GOLD/GAS.
2. После появления usable SPOT source перевести macro markets с `FUTURES_DIRECT` на canonical SPOT-first analysis без изменения пользовательской архитектуры.
3. Встроить `DailyTrendProfileService` 2/3/4 в обязательный final ranking для всех поддерживаемых SPOT markets.
4. Завершить validated historical expectancy engine и накопление статистики по режимам.
5. Добавить отдельный достоверный LONG/SHORT balance source, только если появится качественный источник.
6. Провести реальные controlled live scans на выходных/торговых сессиях и сравнить фактические данные BCS с ожидаемым pipeline contract.
7. После серии наблюдений отдельно валидировать стабильность ranking, trigger/readiness и фактическую полезность TOP-2/3.

### Архитектурные запреты, которые сохраняются

- не встраивать в код цель `20 000 ₽/день` как торговый параметр;
- не превращать scanner score в вероятность прибыли;
- не давать futures определять SPOT direction;
- не создавать synthetic RS или synthetic LONG/SHORT balance;
- не скрывать отсутствие SPOT data под фальшивой маркировкой `SPOT`;
- не добавлять автоматическое исполнение ордеров;
- не добавлять SL/TP/position sizing как часть scanner decision engine;
- не раздувать TOP искусственно до трёх инструментов при отсутствии качественных кандидатов.

---

## 21. CURRENT CHECKPOINT — 30.08.2026

Последовательность последних значимых изменений:

```text
3cdf903  Document RC app architecture and runtime audit
18ef865  Remove obsolete legacy production files
...
802e1c8  Add regression coverage for single-window daily impulse
3386b5a  Fix daily trend impulse regression test data
2bc94ab  Update project passport after daily trend regression fix
e973948  Group macro contracts by market before liquidity-aware selection
```

На локальной машине после синхронизации необходимо выполнить:

```bash
git pull --ff-only origin main
python3 -m compileall -q Program
PYTHONPATH=Program python3 -m pytest -q
```

**Фактически подтверждено 30.08.2026:**

```text
HEAD = e9739481d9ee574e450feb51f4f6ff0d88bbf461
compileall = 0
171 passed in 2.23s
branch = main
HEAD == origin/main
```

Следующий локальный контроль после обновления паспорта должен снова подтвердить `171 passed` и чистый `git status`.

---

## 22. TRADING SAFETY / OPERATING RULE

Проект находится в стадии **контролируемого пользовательского тестирования**, а не доказанной прибыльности.

Сканер не гарантирует ежедневную прибыль и не доказывает цель `20 000 ₽+` в день. Эта цифра является пользовательской целевой метрикой/примером желаемого результата и **не является параметром scanner engine**.

Перед переходом к существенным объёмам необходимы историческая валидация expectancy и серия paper/small-size наблюдений.

Практический принцип:

```text
SCANNER FINDS OPPORTUNITY
        ↓
USER CHECKS CONTEXT
        ↓
USER DECIDES FUTURES / ENTRY / RISK
        ↓
NO AUTOMATIC ORDERS
```

**Главное архитектурное состояние на 30.08.2026:** продукт уже является рабочим RC full-market scanner с покрытием акций и четырёх macro-групп, но macro coverage пока использует честно маркированный futures proxy там, где BCS не отдаёт usable SPOT source. Следующий этап — не менять идею сканера, а довести macro SPOT data path и затем унифицировать ranking/expectancy без нарушения SPOT-first контракта.
