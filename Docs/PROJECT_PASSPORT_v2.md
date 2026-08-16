# TRADER_7_12 PRO

## PROJECT PASSPORT v2 — Актуальный единый контекст

**Дата:** 16.08.2026  
**Репозиторий:** `ilshat-71-wq/Trader_7_12`  
**Локальный путь:** `~/Documents/Trader_7_12`  
**Рабочая ветка:** `agent/futures-expiry-liquidity`  
**Последний опубликованный commit:** `2c2e763` — `Add persistent historical replay and offline report`

---

# 1. ГЛАВНАЯ ЦЕЛЬ

Trader_7_12 Pro — профессиональный утренний scanner/assistant для интрадей-торговли фьючерсами Московской биржи.

Пользователь торгует **фьючерсы**, потому что комиссии по ним ниже, чем по акциям. При этом решение о направлении строится прежде всего по **цене базового актива (SPOT)**, а фьючерс используется как подтверждение возможности реализации сценария.

Главная задача помощника:

> В первые часы торгов быстро найти 2–3 наиболее качественных, ликвидных и потенциально движущихся инструмента, в которых в этот день действительно есть деньги и торговый интерес.

Сканер не принимает решение вместо пользователя. Пользователь сам решает:

- входить или не входить;
- размер позиции;
- риск;
- SL/TP;
- момент исполнения сделки.

---

# 2. ЧТО ТОРГУЕТ ПОЛЬЗОВАТЕЛЬ

Основные классы фьючерсов:

- акции;
- валюта;
- золото;
- нефть;
- газ.

Допускаются другие ликвидные фьючерсы только если они проходят динамический universe и SPOT-first фильтры.

---

# 3. ОСНОВНАЯ ИДЕЯ РЫНКА

Главный поводырь рынка — **индекс полной доходности IMOEX2 / IRUS2**.

Относительная сила/слабость должна отвечать реальному поведению инструмента относительно этого benchmark.

### Сильный инструмент

- рынок растёт → инструмент растёт сильнее рынка;
- рынок падает → инструмент падает слабее рынка / сохраняет относительную устойчивость.

### Слабый инструмент

- рынок падает → инструмент падает сильнее рынка;
- рынок растёт → инструмент растёт хуже рынка / сохраняет слабость.

Торговая идея:

- при росте рынка искать **сильные LONG**;
- при снижении рынка искать **слабые SHORT**.

RS не должен быть искусственным. Если корректный benchmark или данные RS недоступны, система должна писать `RS unavailable`, а не назначать fake value.

---

# 4. ВРЕМЯ РАБОТЫ

Все торговое время проекта — **МСК / Europe/Moscow**.

### Основное окно

**07:00–10:00 МСК**

### Дополнительный мониторинг

**10:00–13:00 МСК**

Приоритет:

1. 07:00–08:00 — раннее обнаружение;
2. 08:00–10:00 — основное торговое окно;
3. 10:00–13:00 — дополнительные подтверждения и новые возможности.

---

# 5. ЧТО ДОЛЖЕН ДЕЛАТЬ СКАНЕР

На контрольных точках scanner должен:

1. загрузить доступную рыночную информацию;
2. сформировать динамический universe;
3. определить SPOT для каждого фьючерса;
4. отфильтровать недостаточно ликвидные инструменты;
5. определить направление и состояние SPOT;
6. сравнить инструмент с benchmark рынка;
7. определить setup;
8. дождаться подтверждения фьючерсом;
9. оценить качество и потенциал движения;
10. ранжировать кандидатов;
11. выдать TOP 2–3.

Главный критерий практической пользы:

> Сканер должен находить инструмент, который сегодня имеет повышенный потенциал движения и в котором есть деньги/объём, чтобы пользователь мог самостоятельно выбрать сделку с хорошим потенциальным процентом движения.

---

# 6. SPOT-FIRST АРХИТЕКТУРА

Жёсткое правило:

`FUTURES → SPOT → SPOT ANALYSIS → FUTURES CONFIRMATION`

Сначала определяется базовый актив и анализируется именно он:

- направление;
- дневной тренд;
- intraday движение;
- ликвидность;
- money volume;
- относительная сила/слабость;
- setup.

Затем фьючерс подтверждает сценарий.

Фьючерс не должен самостоятельно отменять SPOT-first архитектуру.

---

# 7. FUTURES → SPOT MAPPING

Основной сервис:

`Program/services/futures_spot_mapping_service.py`

Mapping должен быть динамическим. Нельзя поддерживать вручную зашитый список фьючерсов.

Использовать достоверные BCS metadata:

- underlying metadata;
- SPOT metadata;
- class code;
- ticker;
- другие подтверждённые поля BCS.

Если SPOT отсутствует, неоднозначен или корректный class code определить нельзя — фьючерс отбрасывается.

Нельзя угадывать SPOT по названию при неоднозначности.

---

# 8. ЛИКВИДНОСТЬ И «ГДЕ ДЕНЬГИ»

Ликвидность — обязательный фильтр.

Ключевой показатель:

`money volume = price × volume`

Учитывать:

- текущий money volume;
- средний дневной money volume;
- SPOT money volume;
- futures money volume;
- устойчивость ликвидности.

Практический смысл:

> Пользователь хочет торговать в тот инструмент, в который в данный день реально зашли деньги и где есть достаточный объём для движения.

Не нужно заполнять TOP-3 малоликвидными контрактами только ради количества.

---

# 9. ДНЕВНЫЙ ТРЕНД

Daily timeframe — базовый фильтр направления и контекста.

Предпочтительно видеть 2–3 дня последовательного движения.

Рабочие состояния:

- `UPTREND`;
- `WEAK_UPTREND`;
- `DOWNTREND`;
- `WEAK_DOWNTREND`.

Задача daily trend — отделять устойчивое движение от случайного intraday шума, не превращая систему в сложную модель.

---

# 10. RELATIVE STRENGTH / WEAKNESS

RS — один из ключевых факторов ranking.

Для LONG предпочтителен реальный `STRONGER`; для SHORT — реальный `WEAKER`.

Важно: текущий исторический replay, который был запущен 16.08.2026, показывает сообщения:

`Historical RS benchmark: IMOEX/INDX (dynamic INDICES metadata)`

и в строках кандидатов встречается `RS 50.00 STRONGER` / `RS -50.00 WEAKER`.

Это означает, что текущая реализация уже подключает benchmark-ветку и влияет на исторический ranking, **но benchmark в фактическом выводе пока определяется как IMOEX/INDX, а не явно IMOEX2/IRUS2**.

Это является текущей задачей верификации/доработки: подтвердить, что для проекта используется именно нужный индекс полной доходности **IMOEX2 / IRUS2**, либо документированно определить корректное BCS metadata-отображение этого benchmark.

Нельзя считать `RS 50/-50` окончательно доказанным качественным RS только по факту наличия поля. Нужно проверить формулу и benchmark.

---

# 11. SETUP

Основные setup:

- `BREAKOUT`;
- `PULLBACK`;
- `REBOUND` — допустим как дополнительный setup.

`REBOUND` не должен автоматически получать преимущество над качественным breakout/pullback.

---

# 12. FUTURES CONFIRMATION

Фьючерс подтверждает SPOT-сценарий.

Учитывать:

- направление;
- цену;
- breakout/pullback state;
- объём;
- качество движения;
- время подтверждения.

Смысл:

`SPOT создаёт идею → FUTURES подтверждает её реализацию`.

---

# 13. RANKING

Основной исторический ranker:

`Program/services/historical_candidate_ranker_service.py`

Рейтинг должен быть лёгким и объяснимым. Учитываются:

- futures confirmation;
- daily trend;
- движение;
- setup;
- SPOT liquidity;
- futures liquidity;
- RS, когда он реально доступен.

Score нужен для выбора лучших 2–3 кандидатов, а не для создания «чёрного ящика».

---

# 14. ЦЕЛЕВОЙ ВЫВОД В 07:00+

Пользователь должен видеть примерно:

```text
TRADER_7_12 PRO — MORNING RADAR
MARKET: IMOEX2 / IRUS2
TIME: 07:45 MSK

MARKET: UP

TOP LONG
1. XXXX — LONG
   SPOT: ...
   FUTURES: ...
   TREND: UPTREND
   RS: STRONGER
   SETUP: PULLBACK
   FUT CONFIRMATION: READY
   MONEY: HIGH
   POTENTIAL: HIGH

TOP SHORT
2. YYYY — SHORT
   SPOT: ...
   FUTURES: ...
   TREND: DOWNTREND
   RS: WEAKER
   SETUP: BREAKOUT
   FUT CONFIRMATION: READY
   MONEY: HIGH
   POTENTIAL: HIGH

3. ZZZZ — LONG/SHORT
   ...

USER DECIDES THE TRADE.
```

Финальный вывод должен быть понятен за несколько секунд.

---

# 15. ЧТО НЕ НУЖНО

Категорически не возвращать в scanner architecture:

- RiskManagementService;
- risk_percent;
- deposit;
- max_position_percent;
- position_value;
- position sizing;
- автоматический расчёт лотов;
- автоматический SL;
- автоматический TP;
- portfolio manager;
- order execution.

Пользователь сам принимает решение по риску, позиции и исполнению.

---

# 16. НЕТ АВТОМАТИЧЕСКОГО ИСПОЛНЕНИЯ

Проект остаётся:

**READ / ANALYSIS / SCANNER ONLY**

Historical replay:

**READ ONLY — NO ORDERS**

---

# 17. MORNING PIPELINE

Основной сервис:

`Program/services/morning_trading_pipeline_service.py`

Назначение:

- получать кандидатов;
- фильтровать неподтверждённые сценарии;
- ранжировать;
- оставлять TOP 2–3;
- ничего не исполнять.

Архитектурные тесты scanner-only должны сохраняться в актуальной форме.

---

# 18. HISTORICAL REPLAY — ТЕКУЩИЙ ПРОГРЕСС 16.08.2026

Сегодня реализовано и опубликовано:

- сохранение replay результатов в JSON;
- offline report без BCS/API вызовов;
- разбивка результатов по confirmation window;
- сохранение `confirmation_window` в каждой записи;
- тесты сервиса;
- `.gitignore` для runtime-файлов replay.

Новые файлы/изменения опубликованы commit:

`2c2e763 Add persistent historical replay and offline report`

Ветка синхронизирована с GitHub.

Runtime-файл:

`Docs/historical_replay/latest_results.json`

не хранится в Git, потому что каталог добавлен в `.gitignore`.

---

# 19. ПОСЛЕДНИЙ HISTORICAL REPLAY

Команда, реально выполненная 16.08.2026:

```bash
PYTHONPATH=Program python3 Program/services/historical_universe_replay_runner.py \
  --dates 2026-08-11,2026-08-12,2026-08-13,2026-08-14 \
  --min-money 100000000 \
  --limit 3
```

Результат:

- 4 даты;
- 12 кандидатов;
- 8 доступных outcomes;
- DIR WIN RATE: **37.5%**;
- AVG DIR: **-0.81%**;
- AVG MFE: **0.04%**.

Разбивка:

- EARLY: 8 candidates / 8 outcomes / 37.5% win rate / -0.81% avg directional return;
- LATE: 4 candidates / 0 outcomes;
- NONE: 0.

### Важный вывод

Этот результат **не подтверждает торговое преимущество текущего ranking pipeline**.

37.5% win rate и отрицательный средний directional return означают, что сейчас нельзя считать алгоритм готовым к реальной торговой эксплуатации.

Это не повод искусственно подкручивать score. Нужно выяснить:

1. корректен ли benchmark RS;
2. корректна ли формула RS;
3. действительно ли SPOT-first setup предсказывает дальнейшее движение;
4. насколько корректно выбрана точка входа/confirmation;
5. достаточно ли хорошо money volume выявляет «инструмент дня»;
6. не переоценивает ли ranking некоторые setup.

---

# 20. ПОСЛЕДНИЕ ИСТОРИЧЕСКИЕ КАНДИДАТЫ ПОСЛЕ ТЕКУЩЕЙ РЕАЛИЗАЦИИ

### 11.08.2026

1. `SSU6 / SMLT` LONG — REBOUND — score 98.00 — RS STRONGER — 13:00 DIR -3.25%
2. `ONZ6 / OZON` LONG — PULLBACK — score 93.40 — RS STRONGER — 13:00 DIR +2.52%
3. `VKU6 / VKCO` LONG — REBOUND — score 93.35 — RS STRONGER — 13:00 DIR -1.76%

### 12.08.2026

1. `ONU6 / OZON` LONG — PULLBACK — score 100.00 — RS STRONGER — 13:00 DIR -1.02%
2. `S0U6 / SOFL` SHORT — BREAKOUT — score 99.07 — RS WEAKER — outcome unavailable
3. `SEU6 / SPBE` LONG — BREAKOUT — score 95.98 — RS STRONGER — 13:00 DIR -4.67%

### 13.08.2026

1. `PXU6 / PLZL` SHORT — BREAKOUT — score 100.00 — RS WEAKER — 13:00 DIR +2.22%
2. `SHU6 / SFIN` SHORT — BREAKOUT — score 100.00 — RS WEAKER — 13:00 DIR +1.03%
3. `SSU6 / SMLT` SHORT — PULLBACK — score 100.00 — RS WEAKER — 13:00 DIR -1.54%

### 14.08.2026

1. `MVU6 / MVID` SHORT — BREAKOUT — score 100.00 — RS WEAKER — outcome unavailable
2. `WUU6 / WUSH` SHORT — BREAKOUT — score 100.00 — RS WEAKER — outcome unavailable
3. `RUU6 / RNFT` SHORT — REBOUND — score 98.40 — RS WEAKER — outcome unavailable

Эти результаты являются диагностическим replay, а не рекомендацией к торговле.

---

# 21. ТЕКУЩЕЕ СОСТОЯНИЕ GITHUB

Рабочая ветка:

`agent/futures-expiry-liquidity`

Последний опубликованный commit:

`2c2e763 Add persistent historical replay and offline report`

До него:

- `fdcf8aa Clean obsolete manual trade test`;
- `3210b17 Clean obsolete legacy signal smoke test`;
- `940debf Clean obsolete legacy signal smoke test`;
- `74ca410 Clean obsolete manual service smoke test`.

Локальный status после push был чистым.

---

# 22. КЛЮЧЕВЫЕ ФАЙЛЫ

Основной scanner:

```text
Program/services/futures_spot_mapping_service.py
Program/services/futures_universe_service.py
Program/services/futures_trade_candidate_service.py
Program/services/futures_confirmation_service.py
Program/services/futures_morning_radar_service.py
Program/services/morning_trading_pipeline_service.py
```

Historical validation:

```text
Program/services/historical_universe_replay_service.py
Program/services/historical_universe_replay_runner.py
Program/services/historical_candidate_ranker_service.py
Program/services/historical_replay_report.py
Program/test_historical_universe_replay_service.py
```

---

# 23. ТЕХНИЧЕСКАЯ СРЕДА

- macOS Sequoia;
- iMac 27 Intel;
- Python 3.14.6;
- PySide6 6.11.1;
- BCS API;
- торговое время проекта — Europe/Moscow.

Короткая обязательная проверка после изменений:

```bash
python3 -m py_compile ...
```

Затем — соответствующий тест/replay.

---

# 24. BCS / СЕТЬ

BCS используется для market data.

Нормальный вывод:

`✅ Авторизация БКС успешна`

Периодически возникают:

`Retry 1: SSLError`

Это считать сетевой/API проблемой, пока не доказано обратное. Не менять алгоритм только из-за единичных SSLError.

---

# 25. АРХИТЕКТУРНЫЕ ПРАВИЛА

Проект должен оставаться:

**простым → быстрым → объяснимым → проверяемым**.

Не добавлять без доказанной пользы:

- ML;
- сложные модели;
- десятки scoring factors;
- portfolio manager;
- risk engine;
- order execution;
- лишние historical layers.

Каждый новый компонент должен отвечать:

> Помогает ли он лучше находить 2–3 лучших инструмента утром?

Если нет — компонент не нужен.

---

# 26. КРИТЕРИЙ ГОТОВНОСТИ

Проект будет считаться готовым к практическому использованию, когда на реальных утренних данных он стабильно способен:

1. динамически сформировать universe;
2. корректно определить SPOT;
3. отфильтровать ликвидные инструменты;
4. определить состояние рынка по IMOEX2/IRUS2;
5. определить реальные сильные/слабые инструменты относительно рынка;
6. найти setup;
7. дождаться futures confirmation;
8. выбрать 2–3 лучших кандидата;
9. показать потенциал движения и где есть деньги;
10. при этом не исполнять сделки и не заниматься risk management.

Historical replay должен показывать положительное и устойчивое преимущество на нескольких независимых торговых днях, а не только отдельные удачные примеры.

---

# 27. ЧТО СЕЙЧАС НУЖНО ПРОВЕРИТЬ ПЕРВЫМ

### Приоритет №1 — benchmark RS

Текущий replay пишет `IMOEX/INDX`, тогда как целевой benchmark проекта — **IMOEX2 / IRUS2**.

Нужно проверить BCS metadata и убедиться, что используется именно индекс полной доходности, а не обычный IMOEX, если BCS предоставляет IRUS2 как отдельный инструмент.

### Приоритет №2 — формула RS

Проверить, что `STRONGER/WEAKER` и числовой RS отражают реальное относительное движение инструмента против benchmark, а не только наличие benchmark candles.

### Приоритет №3 — ranking quality

После исправления/подтверждения RS повторить исторический replay минимум на нескольких завершённых датах и сравнить:

- win rate;
- average directional return;
- MFE;
- результат LONG отдельно;
- результат SHORT отдельно;
- результат BREAKOUT/PULLBACK/REBOUND отдельно;
- EARLY vs LATE;
- влияние money volume.

### Приоритет №4 — morning output

После подтверждения качества historical pipeline привести реальный утренний вывод к короткому TOP 2–3 формату, пригодному для просмотра за несколько секунд.

---

# 28. ЖЁСТКИЕ ПРАВИЛА — НЕ МЕНЯТЬ

1. Главная задача — найти 2–3 лучших инструмента.
2. Торгуются фьючерсы, анализируется базовый SPOT.
3. Главный market benchmark — IMOEX2 / IRUS2.
4. Сильный инструмент — сильнее рынка вверх или устойчивее вниз.
5. Слабый инструмент — слабее рынка вниз или плохо растёт вверх.
6. LONG ищется прежде всего при росте рынка среди сильных.
7. SHORT ищется прежде всего при падении рынка среди слабых.
8. Ликвидность обязательна.
9. Money volume = price × volume — ключевой практический показатель.
10. Universe динамический.
11. SPOT mapping динамический.
12. При неоднозначном SPOT фьючерс отбрасывается.
13. RS должен быть реальным.
14. Если RS unavailable — не придумывать его.
15. Futures confirmation остаётся обязательной частью качественного сценария.
16. Основное окно — 07:00–10:00 МСК.
17. Дополнительное окно — 10:00–13:00 МСК.
18. Historical replay — READ ONLY.
19. Никаких orders в validation.
20. Никакого position sizing/risk management/SL/TP в scanner.
21. Не возвращать obsolete legacy layers.
22. Не усложнять систему без доказанной пользы.
23. Финальный результат должен быть понятен человеку за несколько секунд.

---

# 29. НЕПРИКОСНОВЕННАЯ ЦЕЛЬ

Trader_7_12 Pro не должен превращаться в универсальную торговую платформу.

Это должен быть:

> быстрый профессиональный утренний scanner, который из доступного рынка MOEX находит 2–3 наиболее качественных фьючерсных инструмента с реальной ликвидностью, относительной силой/слабостью и потенциалом движения, после чего пользователь самостоятельно принимает решение о сделке.

---

# 30. ТОЧКА ПРОДОЛЖЕНИЯ

Продолжать работу нужно с проверки фактического состояния Git и кода.

Первый технический вопрос:

> Почему historical replay сейчас показывает benchmark `IMOEX/INDX`, если целевой поводырь проекта — `IMOEX2/IRUS2`?

После этого — проверить реальную формулу RS и повторить multi-date replay.

Только после получения доказанного качества ranking переходить к финальной форме morning radar.
