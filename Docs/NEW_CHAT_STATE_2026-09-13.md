# Trader_7_12 Pro — CURRENT STATE / NEW CHAT MEMO

**Дата контрольной точки:** 2026-09-13  
**Репозиторий:** `ilshat-71-wq/Trader_7_12`  
**Основная ветка:** `main`  
**Последний commit:** `d1946cc5c0b7b5f909c6a1b862b373873b20286b` — `Fix locked futures universe through downstream OI pipeline`  
**Предыдущие ключевые:** `8b5d160` — `Clarify locked-universe admission diagnostics`; `43e915f` — `Enforce locked futures trading universe before OI pipeline`.

## 1. РОЛИ И ПРАВИЛА

Пользователь — автор идеи, требований и торговой логики.  
Ассистент — архитектор и технический руководитель проекта.

Не начинать проект заново. Не создавать отдельные приложения, мини-сканеры, лишние архитектурные слои или параллельные ветки без необходимости.

Главный принцип: **чем проще, тем быстрее, профессиональнее и надёжнее.**

Работать по схеме:

`изменение → тест → фактическая проверка → commit → main`

Пользователь предпочитает терминал, компактные команды и не использует `nano`.

## 2. ЦЕЛЬ

`Trader_7_12 Pro` — единое read-only macOS-приложение для анализа реальных данных MOEX через BCS API.

Главный результат должен быть понятен трейдеру без расшифровки сырых данных:

- какие инструменты сейчас наиболее интересны;
- LONG / SHORT / NEUTRAL;
- насколько сильный сигнал;
- почему сигнал появился;
- изменение сигнала при следующем сканировании.

Приложение **не выставляет заявки**, не управляет позициями и не выполняет торговые действия.

## 3. GIT / СИНХРОНИЗАЦИЯ

GitHub:
`https://github.com/ilshat-71-wq/Trader_7_12.git`

Локальный путь:
`~/Documents/Trader_7_12`

Текущая ветка: `main`.

Последний подтверждённый commit:
`d1946cc5c0b7b5f909c6a1b862b373873b20286b`

История последних ключевых изменений:

- `81b401f` — первоначальный PROJECT_STATE;
- `81bef6a` — исправление BASE underlying mapping diagnostics;
- `5a27116` — автоматическая авторизация BCS;
- `c9f4ba1` — Signal V1: directional signal probability;
- `fbb6880` — исправление macOS build script.

## 4. ТЕКУЩАЯ MACOS APP

Каноническое приложение — **ровно одно**:

`~/Documents/Trader_7_12/dist/Trader_7_12 Pro.app`

Подтверждено 2026-09-13:

- `.app` существует;
- это реальная директория, не symlink;
- старой копии в `~/Applications` нет;
- `origin/main` синхронизирован с `fbb6880`.

Запуск:

```bash
cd ~/Documents/Trader_7_12 && open "dist/Trader_7_12 Pro.app"
```

Build script:
`scripts/build_mac_app.sh`

Последняя проблема с literal `\\n` в первой строке пути исправлена commit `fbb6880`.

## 5. BCS AUTHORIZATION

BCS authorization работает автоматически.

`BCSAPI.headers()` вызывает expiry-aware `authorize()`.

Используется read-only доступ `trade-api-read`.

Access token переиспользуется до истечения срока; refresh выполняется при необходимости. Секреты и refresh token в эту памятку не записывать.

Подтверждённый результат:

- authorization OK;
- защищённый instrument request возвращает HTTP 200;
- SBER lookup возвращает реальные записи.

## 6. BCS DATA POLICY

Только реальные данные.

Запрещено:

- синтетические цены;
- синтетический turnover через `PRICE × VOLUME`, когда для Futures уже есть реальный `VALTODAY`;
- выдуманные ticker/classCode;
- futures как подмена spot/base;
- ручное продвижение неподтверждённых mapping.

BCS HTTP market-data limit — 10 RPS. Для частых запросов BCS рекомендует caching; для потоковых данных — WebSocket. Поэтому concurrency нельзя просто увеличивать без измерения.

BCS WebSocket реально предоставляет:

- последние свечи M1/M5/M15/M30/H1/H4/D/W/MN;
- стакан до 20 уровней;
- поток обезличенных сделок с BUY/SELL.

## 7. SPOT / MARKET RADAR

Основной pipeline:

`BASE/SPOT → D1 → RS vs IMOEX2 → M5 → session price/change → ₽×V → ₽/min → recent 15m flow → liquidity gates → acceleration → current RS → market regime → qualification → ranking`

Ключевые правила:

- BASE/SPOT только реальные BCS instruments;
- Futures не используются как замена Spot;
- hard liquidity gates:
  - `MIN_MONEY_PER_MINUTE = 8_000 ₽/min`
  - `MIN_RECENT_MONEY_PER_MINUTE = 5_000 ₽/min`
- минимальное M5 coverage — 80%.

На закрытом рынке `universe_total=0` и `analyzed=0` — нормальное состояние, а не ошибка.

## 8. FUTURES OI / REAL MONEY FLOW

Источники:

- OI: `MOEX_FUTURES_MARKETDATA_PRIMARY`;
- liquidity: реальный `VALTODAY`;
- mapping: `BCS_CANONICAL_UNDERLYING + MOEX_RFUD_SECID_TO_FAMILY`;
- front contract: `MOEX_RFUD`;
- selection: `MOEX_RFUD_FRONT_NONEXPIRED_NONZERO_OI_PER_FAMILY`;
- money flow: реальные BCS last trades + current order book;
- participant identity claims запрещены.

Ключевые canonical mappings:

- `SR → SBER`
- `GZ → GAZP`
- `SI → USDRUB`
- `EU → EURRUB`
- `CR/CNY → CNYRUB`
- `GD → GLDRUB_TOM`
- `MX/MM/IMOEXF → IMOEX`
- `RI → RTS`
- `NA → QQQ`
- `SF → SPY`
- `USDRUBF → USDRUB`

Некоторые futures-only roots остаются без BASE mapping по дизайну; не считать это автоматически ошибкой.

### Последняя подтверждённая диагностика до locked-universe фикса, 2026-09-13, воскресенье

```text
status: OK
process_status: OK
market_session: CLOSED
raw_contracts: 600
active_contracts: 199
contracts: 233
analyzed: 233
returned: 20
oi_available: 233
liquidity_available: 224
liquidity_top_returned: 20
turnover_source: VALTODAY_ONLY
marketdata_source: MOEX_ISS_FUTURES_MARKETDATA
marketdata_error: None
```

Это означало: **Futures OI pipeline работает, но позже был обнаружен критический дефект downstream re-expansion. Он исправлен commit `d1946cc`.**

`liquidity_available=224/233 ≈ 96.1%`.

В воскресенье:

```text
base_change_available: 0
base_change_missing: 113
base_change_source_counts:
  NOT_BASE_UNDERLYING: 120
  MARKET_CLOSED: 113
```

Это ожидаемо для закрытого рынка и пока не является доказательством неисправности mapping.

Однако текущая диагностика всё ещё помечает:

```text
 data_quality_status: INCOMPLETE
 data_quality_issues: ['INCOMPLETE_UNDERLYING_MAPPING']
 underlying_mapping_coverage_percent: 40.19
```

Это нужно позже сделать честнее: отделить `BASE mapping`, `futures-only`, и `MARKET_CLOSED`.

**Не ломать рабочий OI pipeline ради этого.**

## 9. SIGNAL V1 — ТЕКУЩЕЕ СОСТОЯНИЕ

Commit `c9f4ba1` добавил:

`Program/services/signal_probability_service.py`

и колонки в SPOT/Futures:

`SIGNAL | PROB | ΔPROB`

Сервис использует реальные текущие признаки и deterministic sigmoid model.

ВАЖНО:

`PROB` сейчас — **model probability**, а не статистически калиброванная вероятность будущего движения.

Историческая calibration пока не сделана.

### SPOT features

- price change;
- relative strength;
- money acceleration;
- money/minute;
- recent money/minute;
- daily structure.

### Futures features

- price change;
- ΔOI%;
- money-flow delta;
- money-flow liquidity score;
- position action;
- flow direction.

### Обнаруженный дефект Signal V1

Таблица показала случаи вроде:

`GZ +0.03%, ΔOI -12.36%, COVER ↑ • L → SHORT 58.5%`

`EU +0.03%, ΔOI -10.36%, COVER ↑ • L → SHORT 58.2%`

Это логическое противоречие.

Причина: текущий `SignalProbabilityService` распознаёт внутренние значения:

- `LONG_BUILDUP`
- `SHORT_COVERING`
- `SHORT_BUILDUP`
- `LONG_LIQUIDATION`

но UI/данные ACTION фактически могут приходить как:

- `COVER ↑ • L`
- `LONG ↑ • L`
- `LIQUIDATE ↓ • L`
- `FLOW_ONLY • L`

Следующий шаг — **Signal V1.1**: нормализовать ACTION перед scoring и дать корректные веса:

- LONG BUILDUP → сильный `+`;
- SHORT COVERING / COVER → `+`;
- SHORT BUILDUP → сильный `−`;
- LONG LIQUIDATION / LIQUIDATE → `−`;
- FLOW_ONLY → меньший вес;
- не создавать ложную уверенность при отсутствии реального flow.

Не менять архитектуру. Исправить существующий service и покрыть тестами.

## 10. SIGNAL V1.1 — ВАЖНОЕ ОГРАНИЧЕНИЕ

Не выдавать `70%` как будто это доказанная вероятность.

После накопления исторических наблюдений нужен отдельный этап calibration:

`timestamp → features → model probability → forward return +15/+30/+60m → outcome`

и затем проверка calibration / hit-rate / Brier-style metrics.

До этого UI должен воспринимать PROB как **model confidence/probability**, а не гарантию.

## 11. SPEED / PERFORMANCE — СЛЕДУЮЩИЙ БОЛЬШОЙ ЭТАП

После исправления Signal ACTION и диагностики перейти к скорости.

План:

1. Измерить `timings_seconds` полного scan.
2. Найти реальный bottleneck.
3. Убрать повторные BCS metadata requests.
4. Проверить shared metadata cache.
5. Оптимизировать M5 запросы.
6. Оптимизировать D1 запросы.
7. Проверить bounded concurrency без 429.
8. Снова tests → benchmark → build.

Существующая архитектура уже содержит:

- process-wide BCS API singleton;
- candle cache/retry/bounded concurrency;
- shared metadata cache;
- `MAX_WORKERS = 6`;
- `D1_MAX_WORKERS = 6`;
- timings: `universe`, `benchmark`, `benchmark_d1`, `m5`, `d1`, `calculation`, `total`.

Не увеличивать workers вслепую: BCS HTTP market-data limit — 10 RPS.

## 12. UI

Основные вкладки:

- `RADAR`
- `FUTURES OI`
- `DIAGNOSTICS`
- `SETTINGS`

Текущий стиль: простой, лёгкий, профессиональный.

Не перегружать интерфейс.

Signal columns уже встроены в обе основные таблицы.

## 13. SOUND

Completion melody после полного RADAR + Futures OI workflow уже работает.

Start melody ранее не была подтверждена.

Не возвращаться к этому без необходимости.

## 14. BUILD / RELEASE

Последняя успешная локальная проверка:

- canonical `.app` создан;
- это real directory;
- symlink отсутствует;
- старой копии в `~/Applications` нет;
- Git `HEAD` = `fbb6880` и `origin/main` = `fbb6880`.

После значимых изменений:

```bash
cd ~/Documents/Trader_7_12 && \
pytest -q && \
git diff --check
```

Затем build:

```bash
bash scripts/build_mac_app.sh
```

Проверить:

```bash
test -d "dist/Trader_7_12 Pro.app"
test ! -L "dist/Trader_7_12 Pro.app"
test ! -e "$HOME/Applications/Trader_7_12 Pro.app"
```

## 15. ПОСЛЕДНИЙ ПОДТВЕРЖДЁННЫЙ TEST STATE

Перед Signal V1 commit было:

`121 passed`

После build-script fix приложение успешно собирается в canonical `dist/Trader_7_12 Pro.app`.

После следующих изменений тесты обязательно запускать заново.

## 16. ЧТО НЕ ДЕЛАТЬ

- не начинать проект заново;
- не создавать второе приложение;
- не возвращать `~/Applications/Trader_7_12 Pro.app`;
- не создавать новые мини-сканеры;
- не делать синтетические данные;
- не подменять Spot Futures;
- не выдумывать BCS ticker/classCode;
- не повышать concurrency без контроля 429;
- не называть model probability статистически доказанной вероятностью;
- не менять UI ради косметики, пока backend не стабилен;
- не переписывать рабочий Futures OI pipeline.

## 17. LOCKED FUTURES UNIVERSE — ЗАФИКСИРОВАНО 2026-09-21

Commit `d1946cc5c0b7b5f909c6a1b862b373873b20286b` протянул locked trading universe до самого downstream OI pipeline.

Архитектурный инвариант:

`MOEX/BCS raw futures → policy admission → D-3/front selection → LOCKED contracts → OI → liquidity → TOP 20 → UI`

После admission запрещено повторно использовать широкий MOEX RFUD front set.

`FuturesOIMarketDataScannerService` теперь дополнительно пересекает RFUD `front_contracts` и `curve_contracts` только с `locked_contracts_by_family`.

Ожидаемая диагностика после новой сборки:

```text
trading_universe_candidates: 8
trading_universe_allowed: 8
trading_universe_filtered: 0
active_contracts: 8

moex_working_contracts: 8
contracts: 8
analyzed: 8
returned: <= 8
```

Запрещённые perpetual/auto-roll и foreign/crypto/index futures не должны попадать в Futures OI UI ни при каких downstream fallback paths.

### Следующий этап

После подтверждения новой локальной сборки:

1. `git pull --ff-only origin main`;
2. `pytest -q`;
3. `git diff --check`;
4. build canonical `Trader_7_12 Pro.app`;
5. live scan и проверка Futures OI + Diagnostics;
6. затем вернуться к Signal V1.1 ACTION normalization и скорости.

Не создавать новые ветки, приложения или параллельные сканеры.

## 19. КОМАНДА ДЛЯ НОВОГО ЧАТА

В новом чате достаточно написать:

`Продолжаем Trader_7_12 Pro. Прочитай Docs/NEW_CHAT_STATE_2026-09-13.md и продолжай строго с текущей точки. Не начинай проект заново.`

Главная текущая точка: **locked Futures universe → downstream OI pipeline уже исправлен; подтвердить новой локальной сборкой → затем Signal V1.1 ACTION normalization → speed measurement.**

## 18. КОМАНДА ДЛЯ НОВОГО ЧАТА

В новом чате достаточно написать:

`Продолжаем Trader_7_12 Pro. Прочитай Docs/NEW_CHAT_STATE_2026-09-13.md и продолжай строго с текущей точки. Не начинай проект заново.`

Главная точка старта: **Signal V1.1 ACTION normalization → tests → speed measurement.**


## 20. UI POLISH — 2026-09-21

После подтверждения locked Futures Universe выполнена точечная полировка существующего интерфейса, без изменения торговой логики и без создания нового приложения.

Изменения:

- SESSION status card расширен до 150 px, чтобы полное время HH:MM:SS не обрезалось.
- SETTINGS теперь всегда остаётся интерактивной: premium scan visual не перекрывает вкладку настроек во время RADAR/OI scan; при возврате на RADAR/FUTURES OI/DIAGNOSTICS визуализация снова появляется.
- Premium scan visual теперь использует актуальные торговые окна:
  - Moscow / MOEX: 06:50–23:50 MSK;
  - London / LSE: 08:00–16:30 London time;
  - New York / NYSE: 09:30–16:00 ET.
- Индикатор торгового времени на каждом циферблате привязан к фактическим часовым позициям начала/конца сессии и имеет radial current-time marker; линия больше не начинается от произвольной 12:00 позиции.
- Добавлены regression checks для UI-поведения и торговых окон.

Архитектура и data pipeline не менялись.
