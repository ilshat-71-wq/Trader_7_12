# TRADER_7_12 PRO — PROJECT PASSPORT

**Дата актуализации:** 05.09.2026  
**Репозиторий:** `ilshat-71-wq/Trader_7_12`  
**Ветка:** `main` — единственная рабочая ветка  
**Статус:** production-oriented read-only market-attention scanner

## 1. Назначение

Trader_7_12 Pro отвечает на один вопрос: какие 2–3 базовых инструмента прямо сейчас привлекают наибольшее внимание рынка и кто из них относительно рынка сильнее или слабее.

Сканер только анализирует рынок. Он не выставляет заявки, не управляет позициями, не выбирает фьючерсы и не принимает торговое решение за пользователя.

## 2. Канонический universe

Анализируется только реальный SPOT / BASE ASSET:

```text
1. ALL MOEX TQBR STOCKS
2. GOLD
3. OIL
4. GAS
5. USDRUB
```

GOLD: `GLDRUB_TOM`, если доступен в BCS SPOT metadata. USDRUB: реальный spot-инструмент из BCS metadata. OIL/GAS не подменяются фьючерсами; при отсутствии реального base/spot источника — `UNAVAILABLE`.

В обычную рабочую сессию universe включает реальные TQBR-инструменты. На ДСВД stock-universe дополнительно фильтруется по официальному признаку допуска бумаги к выходной сессии `WEEKENDSESSION`, если этот флаг присутствует в BCS metadata. Бумаги с `WEEKENDSESSION=N` в выходной scan не входят.

Если конкретная версия BCS metadata не отдаёт `WEEKENDSESSION`, запись не удаляется молча: она может быть проверена фактической M5-доступностью. Техническая ошибка получения данных не считается отсутствием торгов.

Фьючерсная metadata, expiry, futures mapping и futures ranking в runtime-сканере отсутствуют.

## 3. Главный алгоритм

```text
BASE/SPOT UNIVERSE
        ↓
CURRENT MARKET SESSION M5 DATA
        ↓
PRICE + CHANGE + ₽×V + ₽×V/MIN
        ↓
RECENT 15-MIN ACTIVITY
        ↓
FLOW ACCELERATION
        ↓
IMOEX2 / IRUS2 MARKET BENCHMARK
        ↓
INTRADAY RELATIVE STRENGTH
        ↓
ATTENTION SCORE
        ↓
STRONGEST → LONG CANDIDATE
WEAKEST   → SHORT CANDIDATE
        ↓
COMPACT WATCHLIST
```

## 4. Benchmark / Relative Strength — обязательное правило

Приоритет benchmark:

```text
1. IMOEX2
2. IRUS2 — fallback только если IMOEX2 недоступен/непригоден
```

```text
RS = asset_current_session_return - benchmark_current_session_return
```

### Источник benchmark

```text
BCS metadata
      ↓
BCS M5 candles
      ↓ если M5 benchmark недоступен
BCS current quote: session open → current price
      ↓ если quote также непригоден
benchmark unavailable
```

Quote fallback использует тот же реальный `IMOEX2` или `IRUS2`, а не прокси. Quote принимается только при наличии open, current price и допустимой свежести timestamp. Синтетический benchmark, futures proxy и вычисление индекса из компонентов запрещены.

Если benchmark недоступен, directional LONG/SHORT selection запрещён.

BCS может возвращать `classCode` не на верхнем уровне metadata, а внутри `boards[]`. Сканер поддерживает оба формата и для `IMOEX2` корректно извлекает реальный `INDX` из `boards[].classCode`.

IMOEX2 является benchmark для дополнительных сессий; MOEX публикует расчёт IMOEX2 в ДСВД.

## 5. Market Attention

`attention_score` — относительная оценка внимания внутри текущего скана, не вероятность прибыли.

Компоненты:

- recent 15-minute ₽×V/min;
- session ₽×V;
- session ₽×V/min;
- ускорение денежного потока.

Приоритет отдаётся текущей активности.

## 6. LONG / SHORT selection

```text
LONG:
  положительный RS относительно benchmark
  высокая текущая активность
  максимальное внимание среди сильных

SHORT:
  отрицательный RS относительно benchmark
  высокая текущая активность
  максимальное внимание среди слабых
```

Сильный актив на падающем рынке может быть LONG-кандидатом. Слабый актив на растущем рынке может быть SHORT-кандидатом.

## 7. Торговый календарь и ДСВД

Календарные суббота/воскресенье не считаются автоматически закрытым рынком. MOEX проводит ДСВД на фондовом рынке с 09:50 до 19:00 МСК; ДСВД является частью ближайшего следующего обычного торгового дня.

По опубликованному календарю 2026 года фондовый рынок не проводит ДСВД 12–13 сентября, 24–25 октября и 28–29 ноября. 5–6 декабря ДСВД проводится. 05.09.2026 является торговым выходным днём.

На фондовой ДСВД доступны основные режимы TQBR/TQTF/TQIF/TQTY и SMAL, а конкретная бумага должна быть допущена к выходной сессии. MOEX прямо указывает, что статус допуска конкретной бумаги можно определить по полю `SECURITIES.WEEKENDSESSION`.

**Критическое правило сканера:** окно `09:50–13:00 MSK` — только предпочтительное окно пользователя для наблюдения/торговли при повышенной активности. Оно **не ограничивает работу сканера**.

Сканер работает в течение всей фактически открытой текущей торговой сессии, начиная с реального `session_start`, который предоставляет `MarketSessionService`, и до фактического закрытия этой сессии.

```text
обычный день:
  MORNING: 07:00 → 10:00 MSK
  MAIN:    10:00 → 19:00 MSK
  EVENING: 19:00 → 23:50 MSK

ДСВД:
  trading/scanning: 09:50 → 19:00 MSK

предпочтительное окно пользователя:
  09:50 → 13:00 MSK
  не является hard gate сканера
```

После 13:00 при открытом рынке сканер продолжает работать; UI только показывает, что предпочтительное окно завершилось. До начала реальной сессии или после её закрытия сканирование не выполняется.

На ДСВД `market_session = WEEKEND_SESSION`; сканер использует начало ДСВД `09:50`, а не обычные `07:00`.

## 8. Output contract

Каждый выбранный актив содержит минимум:

```text
selection_role
spot_ticker
market_group
price
change_percent
benchmark
benchmark_change_percent
relative_strength
relative_strength_status
market_relation
session_money
money_per_minute
recent_money
recent_money_per_minute
money_acceleration
attention_score
data_status
pipeline_version
```

Роли: `LONG_CANDIDATE`, `SHORT_CANDIDATE`, `ATTENTION_WATCH`.

## 9. UI

Главный экран — компактный dashboard с двумя основными карточками LONG/SHORT и коротким списком остальных активных инструментов. Диагностика не должна занимать главный экран.

Предпочтительное окно `09:50–13:00 MSK` отображается отдельно и не используется как ограничение сканирования.

## 10. BCS HTTP / сетевой слой

BCS API использует один process-wide read-only client и ограниченную конкурентность.

Market-data HTTP использует глобальное ограничение старта запросов `0.15 s` между запросами, общее для worker-потоков и GET/POST. Это удерживает нагрузку ниже лимита BCS и предотвращает burst-429.

HTTP helper дополнительно использует переиспользуемый `requests.Session` с connection pool на worker thread, чтобы не выполнять TLS/TCP handshake заново для каждого M5-запроса. Это направлено на устранение наблюдавшихся transient `SSLError` при широком скане.

Техническая ошибка HTTP/SSL не должна интерпретироваться как отсутствие торговли. Частичный scan не считается доказательным полным рыночным результатом.

Сканер не запрашивает futures metadata, не строит expiry universe, не выполняет futures mapping и не запускает дорогой технический pipeline по всему рынку.

## 11. Авторизация

Refresh token:

```text
~/.config/Trader_7_12/bcs_refresh_token
chmod 600
```

Секреты в Git запрещены.

## 12. Runtime safety

Запрещено:

```text
order execution
position sizing
SL/TP automation
futures selection
futures confirmation
synthetic SPOT
synthetic RS
FUTURES_DIRECT fallback
synthetic benchmark
```

Если реального base/spot источника нет: `data_status = UNAVAILABLE`.

## 13. Repository hygiene / synchronization

Разработка ведётся только в `main`. Новые рабочие ветки не создаются.

`Docs/PROJECT_PASSPORT.md` — единственный проектный MD-файл и архитектурный checkpoint. Каждый существенный этап разработки обязан актуализировать этот файл.

GitHub `main` — канонический источник кода. Локальная синхронизация:

```bash
git checkout main
git pull --ff-only
```

## 14. Regression tests

Обязательные проверки:

- strong asset on rising market → LONG;
- strong asset on falling market → LONG;
- weak asset on rising market → SHORT;
- weak asset on falling market → SHORT;
- missing IMOEX2 → IRUS2 fallback;
- missing both benchmarks → no directional candidate;
- every directional candidate contains benchmark and RS;
- attention ranking uses recent/current money;
- no futures instruments enter the universe;
- GOLD/USDRUB use real SPOT metadata;
- unavailable OIL/GAS are not replaced by futures;
- BCS M5 benchmark is preferred;
- BCS live quote can supply the same real benchmark when M5 is unavailable;
- stale benchmark quote is rejected;
- nested BCS `boards[].classCode` is recognized;
- `IMOEX2` nested metadata resolves to `INDX`;
- MOEX `WEEKENDSESSION=N` excludes a stock from DSWD universe;
- 05.09.2026 → `WEEKEND_SESSION`;
- 09:49:59 before DSWD → `CLOSED`;
- 09:50:00 DSWD → `WEEKEND_SESSION`;
- 12.09.2026 → `CLOSED`;
- 28.11.2026 → `CLOSED`;
- 05.12.2026 → `WEEKEND_SESSION`;
- weekend scanner uses `09:50` as session start;
- scanner continues after 13:00 while the current market session remains open;
- preferred 09:50–13:00 window is diagnostic/UI information only and never a scan hard gate;
- candle resilience uses bounded retry and connection pooling;
- read-only scanner contract remains intact.

Before live run:

```bash
python3 -m compileall -q Program
PYTHONPATH=Program python3 -m pytest -q Program
```

## 15. Production validation focus

1. Verify actual BCS metadata for `IMOEX2` / `IRUS2` and canonical base/spot instruments.
2. Verify that BCS stock metadata exposes MOEX `WEEKENDSESSION` and that DSWD universe is filtered accordingly.
3. Verify live M5 flow on an ordinary trading day and DSWD.
4. Verify that transient SSL errors no longer materially reduce M5 coverage.
5. Verify no burst HTTP 429 under full universe load.
6. Require sufficient coverage before publishing directional candidates.
7. If HTTP coverage remains unstable, evaluate BCS WebSocket/streaming current-session data rather than hiding missing data.
8. Measure full scan time and network load.
9. Compact output: 1 LONG, 1 SHORT, maximum 1 ATTENTION_WATCH.
10. Verify that scanning continues after 13:00 during an open MAIN/EVENING session.

## 16. Current checkpoint

```text
Repository:              ilshat-71-wq/Trader_7_12
Branch:                  main ONLY
Project MD:              Docs/PROJECT_PASSPORT.md ONLY
Scanner:                 Market Attention Radar
Pipeline version:        2.2.2
Runtime data:            BASE/SPOT only
Equity universe:         ALL TQBR, DSWD filtered by WEEKENDSESSION
Macro groups:            GOLD / OIL / GAS / USDRUB
Benchmark priority:      IMOEX2 → IRUS2 fallback
Benchmark source:        BCS M5 → BCS live quote
IMOEX2 class code:       INDX (including nested boards[].classCode)
Benchmark mandatory:     YES for directional selection
Primary timeframe:       M5
Recent flow window:      15 min
Current-session scanning: FULL OPEN SESSION → actual close
Preferred window:        09:50 → 13:00 MSK (NOT a hard gate)
Weekend session:         WEEKEND_SESSION 09:50 → 19:00 MSK
Selection:               strongest + weakest vs market
Output:                  LONG + SHORT + compact watchlist
Closed market:           explicit MARKET_CLOSED, no M5 scan
Futures analysis:        REMOVED
Futures mapping:         REMOVED
Order execution:         ABSENT
Read-only:               YES
HTTP market-data throttle: 0.15 s between request starts
HTTP connection pooling: YES, per worker thread
Weekend eligibility:     MOEX SECURITIES.WEEKENDSESSION when exposed by BCS metadata
Git synchronization:     GitHub main is canonical
```

## 17. Live-validation history — 05.09.2026

- MOEX DSWD for 05.09.2026 confirmed as a trading weekend session.
- BCS `IMOEX2 / INDX` M5 confirmed directly with live DSWD candles.
- Scanner v2.2 successfully selected real BASE/SPOT LONG and SHORT candidates with IMOEX2-relative strength.
- First broad DSWD run suffered HTTP 429 burst load and produced only partial coverage (`ANALYZED 79/263`); that result was rejected as incomplete.
- Global request-start throttling was added; subsequent run reached `ANALYZED 197/263` and eliminated the previous mass 429 pattern, but still showed transient SSL failures.
- Current remediation adds per-worker HTTP connection pooling and uses the MOEX `WEEKENDSESSION` eligibility flag to prevent non-trading TQBR securities from entering the DSWD scan.
- Scanner 2.2.2 removes the erroneous 13:00 hard gate: `09:50–13:00` is now only the user's preferred activity window, while scanning follows the full current open market session.
- Regression coverage now explicitly verifies continued scanning after 13:00 during an open MAIN session.
