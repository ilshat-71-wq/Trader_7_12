# TRADER_7_12 PRO — PROJECT PASSPORT

**Дата актуализации:** 29.08.2026  
**Репозиторий:** `ilshat-71-wq/Trader_7_12`  
**Ветка:** `main`  
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

Фьючерс не определяет direction, daily trend, relative strength, SPOT eligibility, setup, trigger, readiness или SPOT ranking.

Для `SIU6` анализируется базовый актив **SI / USD-RUB SPOT**. Фьючерс является только способом реализации выбранного пользователем сценария.

Сильный рост конкретного фьючерса сам по себе не должен превращать его в TOP-кандидата.

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

---

## 6. RELATIVE STRENGTH

Benchmark: `IMOEX2 / IRUS2`.

`relative_strength = instrument_return - benchmark_return`.

- `STRONGER`: RS ≥ +0.20 п.п.;
- `WEAKER`: RS ≤ −0.20 п.п.;
- `NEUTRAL`: промежуточная зона;
- `RS_UNAVAILABLE`: обязательные данные отсутствуют.

LONG должен согласовываться с `STRONGER`, SHORT — с `WEAKER`. Синтетический RS запрещён.

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

---

## 9. SETUP QUALITY

`setup_quality_service.py` содержит bounded deterministic quality scoring. Quality отделена от detection/lifecycle и не должна самостоятельно превращать setup в READY/CONFIRMED.

---

## 10. RANKING

Основной ranking использует `candidate_score`, затем session-level `opportunity_score`.

TOP ограничен тремя кандидатами и не заполняется искусственно.

SPOT ranking не зависит от futures reference metrics. Directional RS является значимым directional factor / tie-break.

Daily 2/3/4-day profile предназначен для усиления ranking как **устойчивость направления**, а не как прогноз гарантированной доходности.

---

## 11. EVENT RISK

`moex_event_risk` является жёстким SPOT eligibility gate до candidate formation/mapping.

Сильный однодневный выброс без устойчивой структуры не должен автоматически становиться качественным кандидатом.

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

---

## 13. LONG / SHORT BALANCE

Фактор используется только при наличии достоверных и своевременных данных. При отсутствии качественного источника значение — `UNAVAILABLE`; синтетическая оценка запрещена.

---

## 14. FUTURES MAPPING

Futures — reference mapping выбранного SPOT-актива.

До `signal_state ∈ {READY, CONFIRMED}` futures mapping очищается из результата. После READY/CONFIRMED могут быть показаны ticker, expiry, days-to-expiry и направление SPOT-сценария.

Фьючерсы не подтверждают SPOT signal. Контракты с `days_to_expiry <= 3` исключаются из reference mapping.

---

## 15. TESTS / REGRESSION

Тесты deterministic и не требуют BCS token, сети или live market data.

Критический regression для daily trend проверяет, что:

```text
110 → 100 → 100   = SHORT для 3-дневного окна
100 → 110 → 100 → 100 = NEUTRAL для 4-дневного окна
```

Следовательно, единичный короткий импульс не создаёт aggregate SHORT.

После исправления тестовых данных ожидаемый полный baseline: **168 passed**.

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

Production services не удаляются только потому, что они не импортируются напрямую из `main.py`: часть используется historical replay, diagnostics и regression tests.

---

## 17. INSTALLED `.APP`

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

## 18. RC UI

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

## 19. CURRENT CHECKPOINT — 29.08.2026

Последовательность текущего RC:

```text
3cdf903  Document RC app architecture and runtime audit
18ef865  Remove obsolete legacy production files
...
802e1c8  Add regression coverage for single-window daily impulse
3386b5a  Fix daily trend impulse regression test data
```

На локальной машине после `git pull --ff-only origin main` необходимо выполнить:

```bash
python3 -m compileall -q Program
PYTHONPATH=Program python3 -m pytest -q Program
```

Ожидаемый результат после синхронизации: **168 passed** и чистый `git status`.

---

## 20. TRADING SAFETY / OPERATING RULE

Проект находится в стадии **контролируемого пользовательского тестирования**, а не доказанной прибыльности.

Сканер не гарантирует ежедневную прибыль и не доказывает цель `20 000 ₽+` в день. Перед переходом к существенным объёмам необходимы историческая валидация expectancy и серия paper/small-size наблюдений.

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
