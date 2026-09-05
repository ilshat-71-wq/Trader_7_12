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

На ДСВД анализируются только фактически доступные через источник инструменты. Отсутствие свечей у недоступной бумаги не считается сигналом.

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

Порядок выбора детерминирован и не зависит от порядка ответа BCS metadata.

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

**Критическая BCS-деталь версии 2.2:** BCS может возвращать `classCode` не на верхнем уровне metadata, а внутри `boards[]`. Сканер обязан поддерживать оба формата и для `IMOEX2` корректно извлекать реальный `INDX` из `boards[].classCode`.

IMOEX2 является корректным benchmark для дополнительных сессий; MOEX рассчитывает IMOEX2 во время дополнительных сессий.

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

## 7. Торговый календарь и сессии

**Критическое правило:** `Saturday/Sunday != CLOSED`.

MOEX проводит дополнительные торговые сессии выходного дня (ДСВД) на фондовом рынке с 09:50 до 19:00 МСК, кроме дат, объявленных Биржей неторговыми. ДСВД является частью следующего обычного торгового дня.

Календарь 2026 учитывает опубликованные изменения: 12–13 сентября и 24–25 октября — неторговые выходные; 28–29 ноября — неторговые из-за переноса технических работ; 5–6 декабря — торговые выходные.

```text
обычный день:
  scan 07:00 → 13:00 MSK

ДСВД:
  trading 09:50 → 19:00 MSK
  scan     09:50 → 13:00 MSK
```

На ДСВД `market_session = WEEKEND_SESSION`; сканер использует начало ДСВД `09:50`, а не обычные `07:00`.

Вне торговой сессии scan не запускается. На закрытом рынке — `РЫНОК ЗАКРЫТ`.

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

## 10. Скорость и BCS

BCS API использует один process-wide read-only client и ограниченную конкурентность. HTTP market data используют bounded concurrency, timeout/retry и cache.

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
- 05.09.2026 10:44 MSK → `WEEKEND_SESSION`;
- 09:49:59 before DSVD → `CLOSED`;
- 09:50:00 DSVD → `WEEKEND_SESSION`;
- 12.09.2026 → `CLOSED`;
- 28.11.2026 → `CLOSED`;
- 05.12.2026 → `WEEKEND_SESSION`;
- weekend scanner uses `09:50` as session start;
- candle resilience test matches configured timeout/retry constants;
- read-only scanner contract remains intact.

Before live run:

```bash
python3 -m compileall -q Program
PYTHONPATH=Program python3 -m pytest -q Program
```

## 15. Production validation focus

Следующий этап — не расширение universe и не добавление фьючерсной логики. Приоритет:

1. Проверка фактического BCS metadata для `IMOEX2` / `IRUS2` и канонических base/spot-инструментов.
2. Проверка живого M5-потока в обычный торговый день и на ДСВД.
3. Проверка BCS live quote fallback для benchmark.
4. Контроль, что каждый LONG/SHORT имеет benchmark и RS.
5. Контроль отсутствия futures fallback для OIL/GAS/GOLD/USDRUB.
6. Измерение полного scan time и сетевой нагрузки.
7. При необходимости переход на BCS WebSocket для текущих M5 данных.
8. Компактный output: 1 LONG, 1 SHORT, максимум 1 ATTENTION_WATCH.

## 16. Current checkpoint

```text
Repository:              ilshat-71-wq/Trader_7_12
Branch:                  main ONLY
Project MD:              Docs/PROJECT_PASSPORT.md ONLY
Scanner:                 Market Attention Radar
Pipeline version:        2.2
Runtime data:            BASE/SPOT only
Equity universe:         ALL TQBR (filtered by actual session availability)
Macro groups:            GOLD / OIL / GAS / USDRUB
Benchmark priority:      IMOEX2 → IRUS2 fallback
Benchmark source:        BCS M5 → BCS live quote
IMOEX2 class code:       INDX (including nested boards[].classCode)
Benchmark mandatory:     YES for directional selection
Primary timeframe:       M5
Recent flow window:      15 min
Regular scan window:     07:00 → 13:00 MSK
Weekend scan window:     09:50 → 13:00 MSK
Weekend session:         WEEKEND_SESSION
Selection:               strongest + weakest vs market
Output:                  LONG + SHORT + compact watchlist
Closed market:           explicit MARKET_CLOSED, no M5 scan
Futures analysis:        REMOVED
Futures mapping:         REMOVED
Order execution:         ABSENT
Read-only:               YES
Git synchronization:     GitHub main is canonical
```

**Главная цель версии 2.2:** корректно работать с реальной структурой BCS metadata, не терять `IMOEX2` из-за вложенного `boards[].classCode`, использовать реальный `INDX` benchmark и при этом сохранять жёсткий запрет на синтетические и фьючерсные прокси.
