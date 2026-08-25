# TRADER_7_12 PRO — PROJECT PASSPORT

**Дата актуализации:** 25.08.2026  
**Репозиторий:** `ilshat-71-wq/Trader_7_12`  
**Рабочая ветка:** `fix/candle-concurrency`

---

## 1. ГЛАВНАЯ ЦЕЛЬ

Trader_7_12 Pro — аналитический scanner/assistant для самостоятельной интрадей-торговли фьючерсами Московской биржи.

Сканер **не сканирует фьючерсный рынок как источник идеи**. Он ищет 2–3 наиболее интересных **базовых актива (SPOT)**, в которых сегодня есть деньги, активность, движение и понятная сила/слабость.

Канонический принцип:

> **Сканер находит ГДЕ смотреть. Пользователь самостоятельно выбирает фьючерс, график и точку входа.**

Приложение не исполняет сделки и не заменяет решение пользователя.

---

## 2. КАНОНИЧЕСКАЯ АРХИТЕКТУРА

```text
SPOT
  ↓
SPOT MONEY / ACTIVITY
  ↓
SPOT DIRECTION / DAILY TREND
  ↓
SPOT RELATIVE STRENGTH / WEAKNESS vs IMOEX2 / IRUS2
  ↓
SPOT H1 STRUCTURE + M5 SETUP
  ↓
TOP 2–3 SPOT OPPORTUNITY WATCHLIST
  ↓
USER SELECTS THE FUTURES CONTRACT
```

**Ключевое правило:** данные, ликвидность, движение и подтверждение фьючерса **не участвуют** в eligibility, direction, RS, setup или ranking базового актива.

Фьючерсный mapping может существовать только как справочная связь `BASE ASSET → соответствующий контракт`, чтобы пользователь понимал, чем потенциально торговать.

---

## 3. ЧТО ИЩЕМ

Кандидат должен иметь как можно больше следующих признаков:

1. `price × volume` / money;
2. необычную текущую активность относительно собственной нормы;
3. достаточную SPOT ликвидность;
4. полезную волатильность и потенциал;
5. направленность и дневный контекст;
6. относительную силу или слабость относительно рынка;
7. качественную SPOT-структуру;
8. pullback/rebound или breakout setup;
9. возможность продолжения движения.

TOP-2/3 — это **watchlist возможностей**, а не список готовых входов. WAIT/WATCH могут оставаться в TOP, если базовый актив проходит обязательные SPOT eligibility-проверки.

Если качественных кандидатов меньше трёх, TOP не заполняется искусственно.

---

## 4. UNIVERSE

Общий universe:

`IMOEX stocks + OIL + GOLD + GAS + USDRUB`

Состав IMOEX загружается динамически через MOEX ISS.

Отдельные market drivers OIL/GOLD/GAS/USDRUB анализируются как самостоятельные SPOT-активы и конкурируют с IMOEX-акциями за общий TOP 2–3.

Нельзя заранее резервировать места по группам.

---

## 5. SPOT MONEY / ACTIVITY

Каноническая метрика:

`money_volume = price × volume`

Учитываются:

- текущий SPOT money volume;
- средний оборот завершённых торговых дней;
- текущий session money volume;
- money volume в единицу времени;
- текущая активность относительно ожидаемой активности.

Ключевой показатель:

`activity_ratio = current_session_money / expected_money_to_now`

Абсолютный оборот не должен автоматически делать актив лидером: важна аномальность текущей активности относительно собственной нормы.

---

## 6. MARKET BENCHMARK — IMOEX2 / IRUS2

Главный benchmark российского рынка — `IMOEX2 / IRUS2`.

Он используется для market context и Relative Strength.

### Сильный SPOT-актив

Для LONG предпочтителен актив, который:

- растёт быстрее рынка при росте рынка;
- падает медленнее рынка при снижении рынка;
- сохраняет относительное превосходство после отката.

### Слабый SPOT-актив

Для SHORT предпочтителен актив, который:

- падает быстрее рынка при снижении рынка;
- растёт хуже рынка при росте рынка;
- сохраняет относительную слабость после отскока.

Формула:

`relative_strength = instrument_return - benchmark_return`

Положительный RS означает превосходство SPOT над benchmark; отрицательный — относительную слабость.

Канонические сигналы:

- `STRONGER` — RS ≥ 0.20 п.п.;
- `WEAKER` — RS ≤ -0.20 п.п.;
- `NEUTRAL` — промежуточная зона;
- `RS_UNAVAILABLE` — обязательные данные benchmark отсутствуют.

Фиктивный RS запрещён.

---

## 7. DIRECTION / DAILY TREND

Daily timeframe — базовый контекст.

Предпочтительны 2–3 последовательных дня движения в одном направлении, но это не абсолютный запрет.

Для ranking RS должен согласовываться с направлением:

- `LONG + STRONGER` — плюс;
- `SHORT + WEAKER` — плюс;
- `LONG + WEAKER` — штраф;
- `SHORT + STRONGER` — штраф.

---

## 8. SPOT STRUCTURE / SETUP

Основной контекст — H1 SPOT.

Формирование текущего сценария — M5 SPOT.

LONG:

`H1 up → impulse → first pullback → stabilization → continuation`

SHORT:

`H1 down → impulse → first rebound → stabilization → continuation`

Рабочая зона retracement ориентировочно 35–75% импульса, с ориентиром около 50%.

Состояния:

- `WAIT` — идея интересна, но setup ещё не сформирован;
- `WATCH` — setup развивается и требует наблюдения;
- `READY` / `CONFIRMED` — setup имеет фактическое подтверждение.

**Setup quality и opportunity score — разные измерения.** Высокий opportunity score не означает готовый вход.

---

## 9. RANKING

Итоговый вопрос:

> **Где сегодня одновременно есть деньги, активность, движение, сила/слабость и качественный SPOT context?**

Итоговый `opportunity_score` формируется session-aware pipeline из существующего SPOT `candidate_score`, текущей активности и направленного движения.

Setup quality выводится отдельно и не используется как обязательный финальный gate TOP-2/3.

Приоритеты остаются:

1. current SPOT money/activity;
2. SPOT strength/weakness vs benchmark;
3. SPOT liquidity/volume;
4. volatility/potential;
5. direction/daily trend;
6. SPOT setup quality;
7. data quality/freshness.

**Фьючерсные trades, futures price movement, futures turnover и futures confirmation не входят в ranking.**

---

## 10. FUTURES MAPPING

Mapping нужен только для справочной связи выбранного базового актива с торговым инструментом пользователя.

Каноническое правило:

> **Сначала выбирается BASE ASSET. Только после этого пользователь самостоятельно выбирает подходящий фьючерсный контракт.**

Фьючерсный mapping не должен менять:

- направление;
- RS;
- score;
- setup;
- TOP ranking.

---

## 11. ДВУХФАЗНЫЙ PIPELINE

### FAST SCREEN

Для universe используются дешёвые SPOT-признаки:

- daily trend;
- average money;
- current SPOT change/momentum;
- preliminary activity;
- preliminary radar score.

### DEEP ANALYSIS

Только лучшие кандидаты получают:

- SPOT RS;
- H1 structure;
- M5 pullback/rebound;
- volatility/potential;
- setup quality;
- detailed session money/activity.

После этого группы объединяются и выбирается TOP 2–3 watchlist.

Сетевые ошибки не должны превращать исправные данные в ложный `NO CANDIDATES`.

---

## 12. ВРЕМЯ

Все торговые времена проекта — `Europe/Moscow`.

Основное окно: **07:00–10:00 МСК**.

Дополнительный мониторинг: **10:00–13:00 МСК**.

---

## 13. ИНТЕРФЕЙС

Интерфейс показывает только информацию о **базовом активе SPOT**:

- тикер SPOT;
- направление;
- opportunity/session score;
- setup и setup state;
- SPOT price;
- SPOT money/activity;
- RS;
- daily context;
- уровни SPOT.

В пользовательском интерфейсе **не выводятся цена, сделки, оборот или движение фьючерса**.

---

## 14. ЧТО ПОЛЬЗОВАТЕЛЬ ДЕЛАЕТ САМ

Пользователь самостоятельно:

- выбирает фьючерсный контракт;
- смотрит его график;
- выбирает точку входа;
- выбирает размер позиции;
- определяет риск;
- устанавливает SL/TP;
- решает, совершать сделку или нет.

Сканер только сокращает поиск.

---

## 15. ЧТО ЗАПРЕЩЕНО

Не добавлять:

- автоматическое исполнение ордеров;
- BUY/SELL команды;
- автоматическую точку входа;
- position sizing;
- управление депозитом;
- автоматический SL/TP;
- portfolio management;
- futures confirmation как обязательный фильтр.

Historical replay — `READ ONLY / NO ORDERS`.

---

## 16. ТЕХНИЧЕСКИЕ ОПОРЫ

Ключевые сервисы:

- `moex_index_universe_service.py` — IMOEX universe;
- `market_trading_universe_service.py` — market groups;
- `futures_spot_mapping_service.py` — справочный mapping;
- `instrument_morning_radar_service.py` — SPOT radar и RS;
- `relative_strength_service.py` — SPOT RS;
- `session_money_volume_service.py` — SPOT session money/activity;
- `spot_first_pullback_service.py` — SPOT setup;
- `two_phase_futures_morning_radar_service.py` — fast/deep pipeline;
- `futures_trade_candidate_service.py` — ranking BASE ASSETS;
- `morning_trading_pipeline_service.py` — итоговый opportunity watchlist;
- `ui.py` — read-only SPOT radar interface.

---

## 17. КАНОНИЧЕСКОЕ ПРАВИЛО ПРОЕКТА

> **Сканер выбирает базовый актив по SPOT. TOP-2/3 показывает лучшие возможности для наблюдения. SETUP STATE сообщает степень готовности, но не превращает watchlist в автоматический вход. Фьючерс выбирает пользователь самостоятельно.**

Это правило имеет приоритет над старыми формулировками.
