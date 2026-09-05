# TRADER_7_12 PRO — PROJECT PASSPORT

**Дата актуализации:** 05.09.2026  
**Репозиторий:** `ilshat-71-wq/Trader_7_12`  
**Ветка:** `main` — единственная рабочая ветка  
**Статус:** production-oriented read-only market-attention scanner

## 1. Назначение

Trader_7_12 Pro отвечает на один вопрос:

> **Какие 2–3 базовых инструмента прямо сейчас привлекают наибольшее внимание рынка, и кто из них относительно рынка сильнее или слабее?**

Сканер **только анализирует рынок**. Он не выставляет заявки, не управляет позициями, не выбирает фьючерсы и не принимает торговое решение за пользователя.

## 2. Канонический universe

Анализируется только реальный SPOT / BASE ASSET:

```text
1. ALL MOEX TQBR STOCKS
2. GOLD
3. OIL
4. GAS
5. USDRUB
```

Для GOLD канонический spot-кандидат — `GLDRUB_TOM`, если он доступен в BCS SPOT metadata.  
Для USDRUB используется реальный spot-инструмент, доступный через BCS metadata.

**OIL/GAS не подменяются фьючерсами.** Если BCS не предоставляет соответствующий base/spot-инструмент, статус должен быть `UNAVAILABLE`, а не `FUTURES_DIRECT`.

Фьючерсная metadata, expiry, futures mapping и futures ranking в runtime-сканере отсутствуют.

## 3. Главный алгоритм

```text
BASE/SPOT UNIVERSE
        ↓
CURRENT SESSION M5 DATA
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
NEXT 1–3 → COMPACT WATCHLIST
```

## 4. Market Benchmark / Relative Strength — обязательное правило

**Каждый анализируемый инструмент всегда сравнивается с индексом рынка Московской биржи.**

Приоритет benchmark жёстко задан:

```text
1. IMOEX2 — основной benchmark
2. IRUS2 — fallback только если IMOEX2 недоступен
```

Порядок выбора не зависит от порядка ответа BCS metadata: сканер сначала пытается использовать `IMOEX2`, и только при отсутствии пригодных текущих M5 данных переходит к `IRUS2`.

Формула:

```text
RS = asset_current_session_return - benchmark_current_session_return
```

Примеры:

```text
market +0.7%, asset +1.8% → RS +1.1 п.п. → сильнее рынка
market -0.6%, asset +0.4% → RS +1.0 п.п. → очень сильный
market +0.7%, asset -0.4% → RS -1.1 п.п. → слабее рынка
market -0.6%, asset -2.2% → RS -1.6 п.п. → очень слабый
```

Если `IMOEX2` и `IRUS2` недоступны или не имеют достаточных свежих M5 данных, directional LONG/SHORT selection **запрещён**. Инструмент нельзя считать сильным или слабым относительно рынка без benchmark.

## 5. Market Attention

`attention_score` — относительная оценка внимания внутри текущего скана, не вероятность прибыли.

Основные компоненты:

- recent 15-minute ₽×V/min;
- session ₽×V;
- session ₽×V/min;
- ускорение денежного потока.

Приоритет отдаётся тому, что происходит **сейчас**, а не только накопленному обороту с открытия.

## 6. LONG / SHORT selection

```text
LONG:
  положительный RS относительно IMOEX2/IRUS2
  высокая текущая активность
  максимальное внимание среди сильных

SHORT:
  отрицательный RS относительно IMOEX2/IRUS2
  высокая текущая активность
  максимальное внимание среди слабых
```

Сильный актив на падающем рынке может быть LONG-кандидатом.  
Слабый актив на растущем рынке может быть SHORT-кандидатом.

`attention_score` не заменяет RS: высокий оборот сам по себе не создаёт направление.

## 7. Текущая сессия

Рабочее окно поиска:

```text
07:00 → 13:00 MSK
```

Основной рабочий таймфрейм:

```text
M5
```

Для каждого актива используются только данные текущей торговой сессии.

Сканер **не запрашивает рыночные свечи, если рынок закрыт**. Выходной день не должен отображаться как активная торговая сессия и не должен порождать массовые пустые M5-запросы.

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

Роли:

```text
LONG_CANDIDATE
SHORT_CANDIDATE
ATTENTION_WATCH
```

## 9. UI

Главный экран — компактный dashboard с двумя основными карточками LONG/SHORT и коротким списком остальных активных инструментов.

Диагностика не должна занимать главный экран.

На закрытом рынке пользователь должен видеть понятный статус `РЫНОК ЗАКРЫТ`, а не ложную активную сессию или ошибку отсутствующего benchmark.

## 10. Скорость и BCS

BCS API использует один process-wide read-only client и ограниченную конкурентность.

Сканер не должен:

- запрашивать futures metadata;
- строить expiry universe;
- выполнять futures mapping;
- делать дорогой технический pipeline для всего рынка.

TQBR остаётся широким universe, но анализ ограничивается свежими M5 market-data запросами и компактным ranking.

BCS документирует лимит 10 RPS для HTTP market data; текущая реализация использует bounded concurrency, timeout/retry и короткий cache, чтобы не сериализовать широкий скан одним запросом и не создавать неконтролируемую нагрузку.

Для частых потоковых данных при следующем performance-этапе приоритетом может быть BCS WebSocket, без изменения алгоритма benchmark/RS и без введения фьючерсных прокси.

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
```

Если реального base/spot источника нет:

```text
data_status = UNAVAILABLE
```

а не прокси через фьючерс.

## 13. Repository hygiene / synchronization

Разработка ведётся **только в `main`**.

Новые рабочие ветки не создаются. Pull Request flow для текущего проекта не используется.

`Docs/PROJECT_PASSPORT.md` — **единственный проектный MD-файл** и архитектурный checkpoint. Каждый существенный этап разработки обязан одновременно актуализировать этот файл.

Лишние futures/macro runtime-модули удалены из основного приложения.

GitHub `main` является каноническим источником кода. Локальные приложения должны синхронизироваться с ним через:

```bash
git checkout main
git pull --ff-only
```

Перед запуском приложение должно находиться на актуальном `main`; локальные незакоммиченные изменения не должны молча перекрывать состояние GitHub.

## 14. Tests

Обязательные regression cases:

- strong asset on rising market → LONG;
- strong asset on falling market → LONG;
- weak asset on rising market → SHORT;
- weak asset on falling market → SHORT;
- missing IMOEX2 → IRUS2 fallback;
- missing both benchmarks → no directional candidate;
- every directional candidate contains benchmark and relative strength;
- attention ranking uses recent/current money;
- no futures instruments enter the universe;
- GOLD/USDRUB use real SPOT metadata;
- unavailable OIL/GAS are not replaced by futures;
- weekend / closed market → `MARKET_CLOSED`, no market-data scan;
- candle resilience test matches the configured timeout/retry constants;
- read-only scanner contract remains intact.

Перед live-запуском на iMac необходимо выполнить:

```bash
python3 -m compileall -q Program
PYTHONPATH=Program python3 -m pytest -q Program
```

## 15. Production validation focus

Следующий этап развития — не расширение universe и не добавление фьючерсной логики. Приоритет:

1. Проверка фактического BCS metadata для `IMOEX2` / `IRUS2` и каждого канонического base/spot-инструмента.
2. Проверка живого M5-потока в день торгов: цена, change, money_volume, recent 15-minute ₽×V/min.
3. Контроль того, что **каждый** LONG/SHORT имеет benchmark и RS относительно `IMOEX2` или `IRUS2`.
4. Контроль отсутствия futures fallback для OIL/GAS/GOLD/USDRUB.
5. Измерение времени полного скана на iMac и исключение лишних сетевых запросов.
6. При необходимости — переход на BCS WebSocket для текущих M5 данных при сохранении того же математического алгоритма.
7. Сохранение компактного output: 1 LONG, 1 SHORT и максимум 1 ATTENTION_WATCH.

Все изменения должны сохранять read-only contract, обновлять этот паспорт и проходить compile + полный pytest.

## 16. Current checkpoint

```text
Repository:              ilshat-71-wq/Trader_7_12
Branch:                  main ONLY
Project MD:              Docs/PROJECT_PASSPORT.md ONLY
Scanner:                 Market Attention Radar
Runtime data:            BASE/SPOT only
Equity universe:         ALL TQBR
Macro groups:            GOLD / OIL / GAS / USDRUB
Benchmark priority:      IMOEX2 → IRUS2 fallback
Benchmark mandatory:     YES for directional selection
Primary timeframe:       M5
Recent flow window:      15 min
Selection:               strongest + weakest vs market
Output:                  LONG + SHORT + compact watchlist
Closed market:           explicit MARKET_CLOSED, no M5 scan
Futures analysis:        REMOVED
Futures mapping:         REMOVED
Order execution:         ABSENT
Read-only:               YES
BCS candle client:       shared / bounded concurrency / cache / timeout
Git synchronization:     GitHub main is canonical
```

**Главная цель версии 2.0:** быстро и честно показать, где находится максимальное текущее внимание рынка, и отделить сильнейший относительно `IMOEX2/IRUS2` актив от слабейшего — без фьючерсной логики и без ложных прокси.