# TRADER_7_12 PRO — PROJECT PASSPORT

**Дата актуализации:** 29.08.2026  
**Репозиторий:** `ilshat-71-wq/Trader_7_12`  
**Ветка:** `main`  
**Назначение:** read-only SPOT-first opportunity scanner / помощник для самостоятельной intraday-торговли фьючерсами Московской биржи.

> Главный принцип: сканер ищет **ГДЕ есть потенциальное преимущество**, а не торгует вместо пользователя. Пользователь самостоятельно выбирает конкретный фьючерс, вход, размер позиции и риск. Исполнение ордеров, SL/TP и position sizing отсутствуют.

---

## 1. ЦЕЛЕВАЯ КОНЦЕПЦИЯ ПОМОЩНИКА

Цель следующего этапа — ежедневно выделять **TOP-2/3 базовых SPOT-инструмента**, где одновременно наблюдаются:

- устойчивый дневной тренд;
- рост/снижение денежной активности и оборота;
- достаточная ликвидность;
- относительная сила/слабость относительно рынка;
- направленный money flow;
- качественный intraday setup;
- подтверждённый trigger;
- положительное историческое математическое ожидание для аналогичных сетапов после накопления достаточной статистики.

**Важно:** текущий `opportunity_score` не является вероятностью прибыли. Вероятность и математическое ожидание должны появиться только после отдельной исторической статистической валидации.

Целевой пользовательский сценарий:

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
MATHEMATICAL EXPECTATION (after validated history)
      ↓
TOP 2–3 SPOT OPPORTUNITIES
      ↓
FUTURES MAPPING — REFERENCE ONLY
      ↓
USER DECIDES WHETHER / WHICH FUTURE TO TRADE
```

---

## 2. SPOT-FIRST / FUTURES BOUNDARY

Фьючерс **не определяет**:

- direction;
- daily trend;
- relative strength;
- SPOT eligibility;
- setup;
- trigger;
- readiness;
- SPOT ranking.

Например, для `SIU6` анализируется базовый актив **SI / USD-RUB SPOT**. Фьючерс может быть показан как инструмент реализации сценария, но решение торговать `SIU6` или не торговать принимает пользователь.

Таким образом, сильный рост конкретного фьючерса сам по себе не должен превращать его в TOP-кандидата.

---

## 3. DAILY TREND — НОВЫЙ КАНОНИЧЕСКИЙ СЛОЙ

Добавлен deterministic network-free сервис:

`Program/services/daily_trend_profile_service.py`

Версия: `1.0`.

Он отдельно измеряет последние **2, 3 и 4 завершённых дневных свечи**.

Для каждого окна рассчитываются:

- `direction`: `LONG / SHORT / NEUTRAL`;
- `state`: `PERSISTENT / CONSISTENT / WEAK / MIXED`;
- изменение цены за окно;
- количество положительных дневных переходов;
- количество отрицательных дневных переходов;
- directional days;
- `consistency_percent`.

Дополнительно рассчитываются:

- согласованность направления между окнами 2/3/4 дня;
- количество persistent windows;
- bounded `score` 0–100.

### Интерпретация

```text
2 дня ↑  → ранний подтверждающий фактор
3 дня ↑  → сильный фактор устойчивого тренда
4 дня ↑  → сильный фактор продолжения

2/3/4 дня ↓ → аналогично для SHORT
```

Один резкий день не должен автоматически считаться устойчивым трендом.

Новый сервис является **детерминированным аналитическим слоем без сети и futures**. Он добавлен безопасно, с regression tests. Следующая задача — подключить его к финальному SPOT ranking вместо/поверх старой упрощённой 3-дневной логики после локальной проверки.

---

## 4. СУЩЕСТВУЮЩИЙ MORNING RADAR

`Program/services/morning_radar_service.py` остаётся базовым источником:

- завершённых D-свечей;
- daily direction;
- daily change;
- average daily money;
- money activity.

Текущая legacy/canonical логика использует `TREND_DAYS = 3` и уже исключает текущую незавершённую дневную свечу.

Новый `DailyTrendProfileService` расширяет это до явного анализа 2/3/4 дней, не ломая существующий контракт.

---

## 5. MONEY / ACTIVITY

Используются/предусмотрены:

- `price × volume`;
- текущий session money volume;
- средний оборот завершённых дней;
- money per minute;
- activity ratio относительно ожидаемой активности.

Абсолютный оборот сам по себе не делает инструмент лидером. Важна активность относительно собственной нормы и качества движения.

---

## 6. MARKET BENCHMARK / RELATIVE STRENGTH

Основной benchmark российского рынка: `IMOEX2 / IRUS2`.

`relative_strength = instrument_return - benchmark_return`.

Canonical interpretation:

- `STRONGER`: RS ≥ +0.20 п.п.;
- `WEAKER`: RS ≤ −0.20 п.п.;
- `NEUTRAL`: промежуточная зона;
- `RS_UNAVAILABLE`: обязательные benchmark data отсутствуют.

LONG должен согласовываться с `STRONGER`, SHORT — с `WEAKER`. Фиктивный RS запрещён.

---

## 7. SETUP / READINESS

H1 задаёт контекст, M5 формирует сценарий.

LONG:

`H1 up → impulse → first pullback → stabilization → continuation`

SHORT:

`H1 down → impulse → first rebound → stabilization → continuation`

Canonical lifecycle:

```text
WAIT → WATCH → ARMED → READY → CONFIRMED
```

`INVALIDATED` — terminal state текущего lifecycle.

`READY/CONFIRMED` — аналитические состояния, а не торговая команда.

---

## 8. TRIGGER / ANTI-CHURN

Главный invariant:

> Trigger level ≠ trigger activation.

```text
LONG  → spot_price >= entry_trigger
SHORT → spot_price <= entry_trigger
```

`MorningTradingPipelineService` использует двухнаблюдательный stability gate:

```text
1-е active observation → ARMED
2-е active observation → READY
```

Обычный transient retreat не уничтожает lifecycle. Explicit invalidation переводит его в `INVALIDATED`; `new_setup=True` начинает новый lifecycle.

---

## 9. SETUP QUALITY

`Program/services/setup_quality_service.py` содержит deterministic bounded quality scoring.

Quality отделена от detection и lifecycle и не должна самостоятельно превращать setup в READY/CONFIRMED.

`SetupEngine` использует quality как enrichment.

---

## 10. RANKING

Основной ranking использует `candidate_score`, затем session-level `opportunity_score`.

TOP ограничен тремя кандидатами и не заполняется искусственно.

SPOT ranking не должен зависеть от futures reference metrics.

Directional RS используется как значимый directional factor / tie-break.

Новый daily 2/3/4-day profile предназначен для усиления ranking именно как **устойчивость направления**, а не как прогноз гарантированной доходности.

---

## 11. EVENT RISK

`moex_event_risk` остаётся жёстким SPOT eligibility gate и проверяется до candidate formation/mapping.

Сильный однодневный выброс без устойчивой структуры не должен автоматически становиться качественным кандидатом.

---

## 12. HISTORICAL REPLAY / MATHEMATICAL EXPECTATION

Historical replay — `READ ONLY / NO ORDERS`.

Historical SPOT candidate формируется и ранжируется до futures lookup.

Следующий статистический этап должен накапливать для каждого типа сетапа:

- количество наблюдений;
- win/loss;
- средний adverse excursion;
- средний favourable excursion;
- средний результат;
- payoff ratio;
- hit rate;
- expectancy;
- результат по LONG/SHORT;
- результат по ликвидности и activity regime;
- результат по 2/3/4-day trend regime.

До достаточной выборки **никакая expectancy не должна отображаться как доказанная вероятность прибыли**.

---

## 13. LONG / SHORT MONEY BALANCE

В архитектуре помощника предусмотрен отдельный фактор для анализа доступных данных о балансе LONG/SHORT.

Он не должен подменять SPOT price action и не должен использоваться, если источник не даёт достоверную и своевременную информацию.

При отсутствии качественных данных значение должно быть `UNAVAILABLE`, а не синтетически вычисляться.

---

## 14. FUTURES MAPPING

Futures — reference mapping выбранного SPOT-актива.

До `signal_state ∈ {READY, CONFIRMED}` futures mapping data очищаются из результата.

После READY/CONFIRMED могут быть показаны:

- futures ticker;
- expiry;
- days to expiry;
- направление соответствующего SPOT сценария.

Futures не подтверждают SPOT signal.

Фьючерсы с `days_to_expiry <= 3` исключаются из reference mapping.

---

## 15. TEST ARCHITECTURE

Regression tests deterministic и не требуют BCS refresh token, сети или live market data.

Текущий baseline после repository cleanup:

```text
163 passed
```

Добавлены отдельные tests для нового daily trend profile:

`Program/test_daily_trend_profile_service.py`

Проверяются:

- persistent LONG на 2/3/4 дня;
- persistent SHORT на 2/3/4 дня;
- смешанная структура;
- insufficient history.

---

## 16. REPOSITORY HYGIENE

Удалены локальные/legacy артефакты:

- `*.bak`;
- `.DS_Store`;
- `.pytest_cache`;
- `__pycache__`;
- старые `Logs`;
- `Docs/historical_replay`;
- ранее удалённые legacy production files.

Не удаляются production services только потому, что они не импортируются напрямую из `main.py`: часть используется historical replay, diagnostics и regression tests.

---

## 17. INSTALLED `.APP`

Установленный bundle:

`/Users/ilshatmac/Applications/Trader_7_12 Pro.app`

Параметры аудита:

```text
CFBundleName:                Trader_7_12 Pro
Version:                     1.4
Bundle ID:                   com.trader712.pro
Architecture:                Mach-O x86_64
```

`.app` является тонким launcher bundle и использует канонический рабочий каталог:

```text
/Users/ilshatmac/Documents/Trader_7_12
```

Launcher устанавливает:

```text
PYTHONPATH=/Users/ilshatmac/Documents/Trader_7_12/Program
```

и запускает текущий:

```text
/usr/bin/env python3 /Users/ilshatmac/Documents/Trader_7_12/Program/main.py
```

BCS refresh token берётся из macOS Keychain и не хранится в Git, app bundle или plist.

`.app` не содержит отдельную копию Python проекта.

---

## 18. RC UI

`Program/watchlist_ui.py` содержит русский SPOT radar UI:

- `SPOT-РАДАР ВОЗМОЖНОСТЕЙ`;
- `ОЦЕНКА ВОЗМОЖНОСТИ`;
- `СИЛА СЦЕНАРИЯ`;
- `РЕКОМЕНДАЦИЯ`;
- `ДЕНЬГИ И АКТИВНОСТЬ`;
- `ОТНОСИТЕЛЬНАЯ СИЛА`;
- `СЕТАП И ТРИГГЕР`.

`ОЦЕНКА ВОЗМОЖНОСТИ` является рейтингом модели, а не статистической вероятностью исхода.

---

## 19. CURRENT CHECKPOINT — 29.08.2026

Новый кодовый слой:

```text
3992fc8  Add deterministic 2-4 day daily trend profile service
b04569d  Add regression tests for 2-4 day trend profile
```

Следующая локальная проверка на iMac должна подтвердить:

```bash
cd ~/Documents/Trader_7_12
git pull --ff-only origin main
python3 -m compileall -q Program
PYTHONPATH=Program python3 -m pytest -q Program
```

После этого можно переходить к следующему шагу: **подключить 2/3/4-day profile непосредственно в TOP-2/3 SPOT ranking**, а затем отдельно добавить validated expectancy из historical replay.

---

## 20. ПРОФЕССИОНАЛЬНЫЙ ПРИНЦИП ПРОЕКТА

Trader_7_12 Pro не должен пытаться угадывать каждый день направление цены.

Он должен искать повторяемые ситуации, где одновременно сходятся:

**тренд + деньги + ликвидность + относительная сила + структура + trigger + статистически подтверждённое преимущество.**

Финальная задача помощника — не сказать пользователю «покупай фьючерс», а дать ему прозрачный shortlist:

```text
№1 — базовый актив — направление — score — почему
№2 — базовый актив — направление — score — почему
№3 — базовый актив — направление — score — почему
```

И отдельно показать, какие данные подтверждают или опровергают сценарий.
