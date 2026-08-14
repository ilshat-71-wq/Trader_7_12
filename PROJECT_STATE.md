# Trader_7_12 Pro — PROJECT_STATE

> Главный паспорт проекта. Используется для продолжения разработки в новом чате без восстановления старой переписки.
> Обновлять после каждого значимого рабочего этапа.
>
> **ВАЖНО:** этот документ описывает НОВУЮ целевую архитектуру Trader_7_12 Pro. Старая архитектура `trade_score / signal / confirmation / breakout / ranker` больше не является основой проекта.

## 1. ЦЕЛЬ ПРОЕКТА

Trader_7_12 Pro — утренний торговый помощник для торговли фьючерсами MOEX через BCS API.

Главная задача:

> Найти утром 2–3 наиболее качественные торговые ситуации, определить направление базового SPOT-актива, дождаться качественной точки входа и предложить соответствующий ликвидный фьючерс для исполнения.

Система не обязана давать сделку каждый день. `NO TRADE` — полноценный и правильный результат.

Основное торговое окно: **07:00–13:00 МСК**.
Главный фокус: **07:00–10:00 МСК**.
Период 10:00–13:00 — мониторинг уже найденных кандидатов и поиск дополнительных возможностей.

Ориентиры проекта:
- депозит около 1 000 000 ₽;
- желаемый результат порядка 15–20 тыс. ₽ в день;
- ориентир 300–600 тыс. ₽ в месяц.

Финансовые цели не должны подгонять систему под нужное количество сигналов.

---

## 2. ГЛАВНЫЙ ПРИНЦИП

**Мы торгуем фьючерсы, но торговая идея сначала формируется на SPOT.**

Фьючерс — инструмент исполнения сделки.

Главная философия:

> Не искать самый быстро растущий или падающий фьючерс. Искать сильный или слабый базовый актив, определить вероятность продолжения его движения, дождаться качественной точки после коррекции или ретеста и только затем выбрать ликвидный фьючерс для исполнения.

Целевая цепочка:

**РЫНОК → FUTURES UNIVERSE → FUTURES↔SPOT MAPPING → SPOT ANALYSIS → SPOT TRADE IDEA → PROBABILITY → FUTURES CONFIRMATION → ENTRY/STOP/TARGET/RR → TOP 2–3 → TRADE → OUTCOME → JOURNAL**

---

## 3. ГЛАВНЫЕ ТОРГОВЫЕ ПРАВИЛА

1. Торгуем только фьючерсами; SPOT — источник идеи.
2. Для каждого futures определяем базовый SPOT.
3. Universe динамический, без фиксированного списка из семи инструментов.
4. Momentum SPOT прежде всего определяет направление.
5. Дневной график задаёт контекст; желательно 2–3+ дня движения в одну сторону.
6. IMOEX — benchmark; Relative Strength только подтверждает/ослабляет идею.
7. Ликвидность обязательна.
8. `money_volume = price × volume` обязателен как фактор интереса/подтверждения, но сам сигнал не создаёт.
9. Не догоняем вертикальный импульс.
10. LONG: сильное движение вверх → первый pullback → подтверждение продолжения → LONG futures.
11. SHORT: сильное движение вниз → первый rebound → подтверждение продолжения снижения → SHORT futures.
12. Breakout — отдельный сценарий: breakout → возврат к уровню → retest → confirmation → entry.
13. Futures может подтвердить, не подтвердить или заблокировать SPOT-идею, но не менять её направление.
14. Показываем модельные `LONG probability %` и `SHORT probability %`.
15. Качество важнее количества; Morning Radar выдаёт максимум 2–3 лучших идеи.
16. `NO TRADE` — нормальный результат.
17. `EARLY` — наблюдение, не готовая сделка.

---

## 4. DYNAMIC FUTURES UNIVERSE

Universe строится динамически из доступных MOEX futures.

Исключаются:
- expired;
- технические/служебные;
- неподходящие для стратегии;
- perpetual и иные неподходящие типы;
- недостаточно ликвидные;
- иные неисполняемые контракты.

Никакого `DEFAULT_INSTRUMENTS = {...}` как основы стратегии.

Тестовый список допустим только отдельно для разработки.

---

## 5. FUTURES ↔ SPOT MAPPING

Для каждого подходящего futures автоматически определяется базовый SPOT.

Mapping — отдельный архитектурный слой.

Примеры только для понимания:
- SRU6 → SBER
- LKU6 → LKOH
- RNU6 → ROSN
- TTU6 → TATN
- PXU6 → PLZL
- SGU6 → SNGSP
- YDU6 → YDEX

Эти примеры не являются фиксированным universe.

Если mapping неоднозначен или отсутствует — контракт не допускается к торговой идее.

---

## 6. SPOT ANALYSIS

Для базового актива анализируем:
- текущую цену;
- изменение цены;
- дневной тренд;
- длительность движения;
- силу движения;
- 5M momentum;
- volume;
- money volume;
- изменение money volume;
- Relative Strength vs IMOEX;
- ускорение/замедление;
- breakout;
- pullback/rebound;
- retest;
- качество setup;
- подтверждение продолжения.

Главный вопрос:

> **Куда с большей вероятностью пойдёт базовый актив — вверх или вниз — и насколько высока оценка модели?**

---

## 7. ДНЕВНОЙ КОНТЕКСТ

Дневной график нужен для контекста, а не для немедленного входа.

Предпочтительно:
- 2–3+ последовательных дня движения;
- понятная структура;
- подтверждающий объём;
- достаточная величина движения.

Текущий незавершённый день не используется в historical daily baseline.

---

## 8. MOMENTUM

**Momentum SPOT прежде всего определяет направление.**

Положительный → кандидат LONG.

Отрицательный → кандидат SHORT.

Сильный momentum не означает немедленный вход.

Старый Trade Score не имеет права самостоятельно создавать LONG/SHORT.

---

## 9. RELATIVE STRENGTH vs IMOEX

IMOEX используется как benchmark.

Если IMOEX растёт:
- актив растёт быстрее → относительная сила;
- актив растёт слабее → относительная слабость.

Если IMOEX падает:
- актив падает меньше → относительная сила;
- актив падает сильнее → относительная слабость.

RS не создаёт сделку самостоятельно.

---

## 10. НЕ ДОГОНЯТЬ ИМПУЛЬС

LONG:

**сильный рост → первый нормальный откат → стабилизация → подтверждение возобновления → LONG futures.**

SHORT:

**сильное падение → первый нормальный отскок → отказ/слабость отскока → подтверждение возобновления снижения → SHORT futures.**

Главная модель входа:

> **Сильное движение → коррекция → подтверждение → вход.**

---

## 11. SETUPS

### FIRST PULLBACK

`IMPULSE UP → FIRST PULLBACK → HOLD/STABILIZATION → CONTINUATION → LONG`

### FIRST REBOUND

`IMPULSE DOWN → FIRST REBOUND → REJECTION/WEAKNESS → CONTINUATION DOWN → SHORT`

### BREAKOUT → RETEST

`TREND → CONSOLIDATION → BREAKOUT → RETURN TO LEVEL → RETEST → CONFIRMATION → ENTRY`

Простой breakout без подтверждения не означает немедленный вход.

---

## 12. VOLUME / MONEY VOLUME

Ликвидность обязательна.

Учитываем:
- volume;
- текущий/средний volume;
- volume ratio;
- money volume;
- изменение money volume.

`money_volume = price × volume`

Желательно, чтобы money volume рос вместе с направленным движением.

Объём и money volume не создают направление самостоятельно.

Старые фиксированные пороги RatingService не считать окончательной торговой системой.

---

## 13. PROBABILITY ENGINE

Для кандидата должны быть:
- `LONG probability: XX%`;
- `SHORT probability: YY%`;
- `NO TRADE / uncertainty` при недостаточном перевесе.

Это модельная вероятность/уверенность, а не обещание результата.

Факторы первого этапа:
- daily trend;
- duration;
- move strength;
- momentum;
- volume;
- money volume;
- RS;
- IMOEX;
- pullback/rebound quality;
- breakout/retest;
- continuation;
- volatility;
- liquidity;
- futures confirmation.

После накопления outcome-журнала probability можно калибровать статистически.

---

## 14. FUTURES CONFIRMATION / EXECUTION

После SPOT trade idea выбирается соответствующий futures.

Проверяем:
- ликвидность;
- volume;
- money volume;
- цену;
- spread;
- basis;
- активность;
- соответствие направления SPOT;
- исполнимость;
- entry/stop/target при необходимости.

Futures может подтвердить, не подтвердить или заблокировать SPOT-идею.

Futures не может самостоятельно изменить направление SPOT.

---

## 15. ENTRY / STOP / TARGET / RR

Для подтверждённого setup постепенно определяем:
- Entry;
- Stop;
- Target;
- invalidation;
- RR.

Главное на раннем этапе — корректно определить setup и состояние входа.

---

## 16. СОСТОЯНИЯ

Минимальные состояния:
- `NO TRADE`;
- `WAIT PULLBACK`;
- `WAIT REBOUND`;
- `WAIT RETEST`;
- `WAIT CONFIRMATION`;
- `ENTRY READY`;
- `BLOCKED`.

`EARLY` — наблюдение.

Старая схема `EARLY / WATCH / STRONG_TRADE / EXECUTE` не является целевой.

---

## 17. TOP 2–3

Morning Radar выдаёт максимум 2–3 лучшие подтверждённые идеи.

Не создавать сигналы ради выполнения нормы.

0 качественных идей → `NO TRADE`.

---

## 18. ЦЕЛЕВОЙ ВЫВОД

### SPOT
- базовый актив;
- направление;
- daily trend;
- move strength;
- momentum;
- volume;
- money volume;
- RS vs IMOEX;
- stage of move;
- setup;
- LONG probability;
- SHORT probability.

### FUTURES
- контракт;
- ликвидность;
- цена;
- spread/basis при наличии;
- подтверждение;
- исполнимость.

### TRADE IDEA
- LONG / SHORT / NO TRADE;
- state;
- Entry;
- Stop;
- Target;
- RR;
- подтверждение;
- invalidation.

---

## 19. ЦЕЛЕВАЯ АРХИТЕКТУРА

```text
MARKET DATA / BCS
        ↓
FUTURES UNIVERSE
        ↓
FUTURES ↔ SPOT MAPPING
        ↓
SPOT ANALYSIS
        ↓
DAILY TREND + MOMENTUM + RS/IMOEX
        ↓
VOLUME / MONEY VOLUME
        ↓
STAGE OF MOVE
        ↓
PULLBACK / REBOUND / BREAKOUT
        ↓
RETEST / CONTINUATION CONFIRMATION
        ↓
PROBABILITY ENGINE
        ↓
SPOT TRADE IDEA
        ↓
FUTURES CONFIRMATION / SELECTOR
        ↓
ENTRY / STOP / TARGET / RR
        ↓
TOP 2–3
        ↓
TRADE
        ↓
OUTCOME
        ↓
JOURNAL
```

---

## 20. LEGACY-АРХИТЕКТУРА

Старые компоненты не являются неприкосновенными:
- `TradeScoreService`;
- `SignalEngine`;
- `TradeDecisionEngine`;
- `TradeRankerService`, если появится/обнаружится в актуальной ветке;
- `VolumeScanner`, если присутствует в локальной рабочей копии;
- дублирующие filters/confirmation;
- старые rating/score-поля.

Не сохранять код только ради совместимости.

Не допускать нескольких конкурирующих систем, независимо считающих score/signal/confidence и затем складывающих результаты.

---

## 21. ЧТО СОХРАНЯЕМ

Без необходимости не ломаем:
- `Program/api/bcs_api.py`;
- `Program/api/request_helper.py`;
- `Program/config.py`;
- авторизацию BCS;
- загрузку инструментов;
- получение futures/spot;
- quotes;
- trades;
- 5M candles;
- daily history;
- IMOEX/IMOEXF;
- обработку дат/времени;
- проверенные API-адаптеры.

---

## 22. ВРЕМЯ

Все торговые правила — **Europe/Moscow**.

UTC используется как технический формат API.

Daily baseline строится только по завершённым торговым дням.

---

## 23. AUDIT — ЭТАП 1

### KEEP / фундамент

**KEEP:**
- `Program/api/bcs_api.py` — рабочая BCS-интеграция;
- `Program/api/request_helper.py` — API helper;
- `Program/config.py` — конфигурация/секреты;
- `Program/services/instrument_service.py` — источник инструментов, но будет расширен для futures universe;
- `Program/scanner/instrument_loader.py` — загрузка инструментов, проверить overlap с InstrumentService;
- `Program/services/candle_service.py` — построение закрытых 5M свечей из trades;
- `Program/services/history_candle_service.py` — daily/history/timezone/baseline;
- `Program/services/candle_loader_service.py` — оставить до проверки зависимостей;
- quote/trade/live market-data services — сохранить как data layer;
- `Program/services/relative_strength_service.py` — сохранить и адаптировать под новый SPOT-first flow;
- `Program/market/market_data.py` и `market_loader.py` — сохранить как market-data foundation после проверки зависимостей.

### REPLACE / REFACTOR

**REPLACE или глубоко REFACTOR:**
- `Program/scanner/scanner_engine.py` — сейчас смешивает instrument loading, quote/trades, rating, candles, momentum, SignalEngine и TradeDecisionEngine;
- `Program/scanner/signal_engine.py` — старый score-based signal layer;
- `Program/scanner/trade_decision_engine.py` — старый final gate, завязанный на trade_score/rating/breakout/confidence;
- `Program/services/instrument_morning_radar_service.py` — содержит `DEFAULT_INSTRUMENTS` из 7 тикеров и не соответствует dynamic universe;
- `Program/services/morning_radar_service.py` — сохранить полезную history/time logic, но переписать ответственность под SPOT analysis;
- `Program/services/breakout_service.py` и `breakout_quality_service.py` — сохранить полезные detection идеи, но проверить и встроить в единый Setup Engine;
- `Program/services/final_trade_service.py` — проверить после нового futures confirmation/risk layer, не переносить старую gate-логику автоматически.

### DISABLE / вывести из нового runtime path

До появления нового ядра отключить от основной торговой цепочки:
- старый `ScannerEngine` pipeline;
- `SignalEngine`;
- `TradeDecisionEngine`;
- старую seven-instrument `InstrumentMorningRadarService` flow;
- UI dependency на старый scanner.

Старые файлы пока физически не удалять.

### DELETE LATER / после проверки зависимостей

После миграции и успешного тестового прогона можно удалить:
- реально неиспользуемые legacy score/filter модули;
- дублирующие `.bak`/backup runtime files, если они не нужны как архив;
- старые сервисы, которые полностью заменены новым ядром.

`Program/backups/` пока не трогать: это архив, а не runtime.

### ВАЖНОЕ НАБЛЮДЕНИЕ

В актуальном дереве `release-0.2` фактически используется структура `Program/...`. Старый `PROJECT_STATE` ссылался на корневые `api/`, `services/`, `scanner/`, что было неточно. С этого этапа паспорт использует фактические пути `Program/...`.

В актуальном дереве обнаружены:
- `Program/scanner/scanner_engine.py` — 15 KB;
- `Program/scanner/signal_engine.py` — 6.6 KB;
- `Program/scanner/trade_decision_engine.py` — 28.9 KB;
- `Program/services/instrument_morning_radar_service.py` — 18.6 KB;
- `Program/services/history_candle_service.py` — 21.3 KB;
- `Program/services/candle_service.py` — 6.1 KB.

В `Program/ui.py` текущий UI импортирует `VolumeScanner` и отображает старые `signal/confidence/trade_score/confirmation/breakout` поля. Значит UI будет переведён на новый Radar только после стабилизации backend.

В текущей ветке поиск по имени `TradeRankerService` не дал совпадения; не создавать его заново без необходимости.

---

## 24. ТЕКУЩИЙ РЕАЛЬНЫЙ СТАТУС

Дата: **2026-08-14**

Репозиторий: `Trader_7_12`
Рабочая ветка: `release-0.2`

### Подтверждено ранее
- BCS authorization: OK;
- instruments pages 0–4: HTTP 200;
- ранее загружено 470 инструментов;
- market data pipeline уже умеет получать quote/trades/candles;
- 5M CandleService умеет исключать незакрытую свечу;
- HistoryCandleService работает с Europe/Moscow и исключением текущего дня;
- Relative Strength и IMOEXF уже существуют как отдельные технические компоненты.

### Этап 1 — результат

**Новая архитектура зафиксирована в PROJECT_STATE.**

**Audit KEEP / REPLACE / DISABLE / DELETE выполнен на уровне текущего GitHub tree и ключевых файлов.**

Главный вывод:

> Рабочую BCS/data/history инфраструктуру сохраняем. Старое score/signal/decision ядро не переносим в новую систему. Следующий кодовый этап — dynamic futures universe.

---

## 25. СЛЕДУЮЩИЕ ЭТАПЫ

### Этап 2 — DYNAMIC FUTURES UNIVERSE

Создать отдельный слой, который:
- получает доступные futures;
- фильтрует expired/technical/неподходящие;
- оценивает ликвидность;
- подготавливает кандидатов для mapping.

### Этап 3 — FUTURES ↔ SPOT MAPPING

Автоматически определить базовый SPOT для каждого futures.

### Этап 4 — SPOT ANALYSIS

Единый аналитический слой базового актива.

### Этап 5 — SETUP ENGINE

Impulse / first pullback / first rebound / breakout / retest / continuation.

### Этап 6 — PROBABILITY ENGINE

Направленные LONG/SHORT probability и NO TRADE.

### Этап 7 — FUTURES CONFIRMATION / SELECTOR

SPOT↔FUTURES consistency, liquidity, spread/basis, execution.

### Этап 8 — RANKING

Лучшие подтверждённые идеи.

### Этап 9 — ENTRY / RISK

Entry / Stop / Target / RR / invalidation.

### Этап 10 — MORNING RADAR / UI

TOP 2–3 понятных торговых идеи.

### Этап 11 — OUTCOME / JOURNAL

Сохранение результатов.

### Этап 12 — CALIBRATION

Калибровка probability по реальным outcomes.

---

## 26. ПРАВИЛО РАЗРАБОТКИ

Работаем по одному логически законченному изменению:

1. изменить один файл/узкий участок;
2. `python3 -m py_compile ...`;
3. тестовый прогон;
4. проверить фактический результат;
5. commit;
6. следующий этап.

Не закрывать терминал через `exit` и не использовать `&& exit`.

---

## 27. ФОРМАТ STATE UPDATE

После каждого значимого этапа:

`Дата:`
`Этап:`
`Что сделано:`
`Что проверено:`
`Результат:`
`Commit:`
`Следующий шаг:`

---

## 28. ФИНАЛЬНОЕ ПРАВИЛО

> **Trader_7_12 Pro не пытается напрямую предсказывать фьючерс. Сначала система ищет качественную ситуацию в базовом SPOT-активе, определяет направление и модельную вероятность продолжения, ждёт нормальный pullback/rebound или подтверждённый breakout/retest, затем проверяет соответствующий ликвидный фьючерс и использует его как инструмент исполнения. Итогом должны быть 2–3 лучшие торговые идеи либо NO TRADE.**
