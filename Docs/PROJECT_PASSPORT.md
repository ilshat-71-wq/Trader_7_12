# TRADER_7_12 PRO — PROJECT PASSPORT

**Дата актуализации:** 28.08.2026  
**Репозиторий:** `ilshat-71-wq/Trader_7_12`  
**Ветка:** `main`  
**Назначение:** read-only SPOT-first opportunity scanner для самостоятельной intraday-торговли фьючерсами Московской биржи.

> Сканер находит ГДЕ смотреть. Пользователь самостоятельно выбирает фьючерс, график, вход и риск. Исполнение ордеров, SL/TP и position sizing отсутствуют.

---

## 1. КАНОНИЧЕСКАЯ АРХИТЕКТУРА

```text
SPOT
 ↓
MONEY / ACTIVITY
 ↓
DIRECTION / DAILY TREND
 ↓
RS vs IMOEX2 / IRUS2
 ↓
H1 STRUCTURE + M5 SETUP
 ↓
TRIGGER LEVEL
 ↓
TRIGGER ACTIVE / CROSSED
 ↓
ANTI-CHURN STABILITY
 ↓
READY / CONFIRMED
 ↓
TOP 2–3 SPOT WATCHLIST
 ↓
FUTURES MAPPING ONLY
```

Фьючерс не определяет direction, RS, eligibility, setup, trigger, readiness или SPOT ranking.

---

## 2. SPOT MONEY / ACTIVITY

Используются `price × volume`, текущий session money volume, средний оборот завершённых дней, money per minute и activity ratio относительно ожидаемой активности к текущему моменту.

Абсолютный оборот сам по себе не делает инструмент лидером: важна активность относительно собственной нормы.

---

## 3. MARKET BENCHMARK / RS

Benchmark российского рынка: `IMOEX2 / IRUS2`.

`relative_strength = instrument_return - benchmark_return`.

- `STRONGER`: RS ≥ +0.20 п.п.;
- `WEAKER`: RS ≤ −0.20 п.п.;
- `NEUTRAL`: промежуточная зона;
- `RS_UNAVAILABLE`: обязательные benchmark data отсутствуют.

Direction и RS должны быть согласованы: LONG + STRONGER, SHORT + WEAKER. Фиктивный RS запрещён.

---

## 4. SETUP / READINESS

H1 задаёт контекст, M5 формирует сценарий.

LONG: `H1 up → impulse → first pullback → stabilization → continuation`  
SHORT: `H1 down → impulse → first rebound → stabilization → continuation`

На уровне setup сохраняются `WAIT`, `WATCH`, `READY`, `CONFIRMED`. На уровне canonical signal lifecycle используются `WAIT`, `WATCH`, `ARMED`, `READY`, `CONFIRMED`, а также terminal `INVALIDATED`.

`READY/CONFIRMED` — аналитические состояния, не торговая команда.

---

## 5. CANONICAL SPOT SIGNAL CONTRACT

Файл: `Program/services/spot_signal_contract.py`.

Это deterministic network-free contract для нормализации direction/setup, directional RS, trigger presence, directional activation/crossing, trigger transition, invalidation, lifecycle и quality aggregation. Контракт не обращается к BCS, сети, futures или live market-data.

### Lifecycle

```text
WAIT
 ↓
WATCH
 ↓
ARMED
 ↓
READY
 ↓
CONFIRMED
```

`INVALIDATED` — terminal state текущего lifecycle. После invalidation возврат в `READY/CONFIRMED` запрещён без явного `new_setup=True`.

### Trigger invariant

> **Trigger level ≠ trigger activation.**

```text
LONG  → spot_price >= entry_trigger
SHORT → spot_price <= entry_trigger
```

`trigger_transition()` разделяет `trigger_crossed`, `trigger_active`, `trigger_state`, `trigger_rearmed` и `trigger_invalidated`.

Обычный откат после activation не является invalidation. Он может re-arm trigger, но не уничтожает lifecycle.

---

## 6. SETUP QUALITY

Файл: `Program/services/setup_quality_service.py`.

Quality отделена от detection и lifecycle. Canonical aggregation использует bounded компоненты `0..100`; отдельный SetupQualityService использует geometry 30%, candle 25%, rejection 20%, continuation 25%.

`SetupEngine.analyze()` обогащает setup candidate quality на том же подготовленном candle window. Quality deterministic/network-free, не переводит setup в READY/CONFIRMED и не меняет earliest READY selection.

---

## 7. RANKING

Основной ranking score — `candidate_score`, затем session-level `opportunity_score`.

Directional RS используется как tie-break. TOP ограничен тремя кандидатами и не заполняется искусственно. Futures metrics не входят в SPOT ranking.

Quality — прозрачный bounded SPOT input с небольшим setup bonus и не может заменить activity, money или directional RS. Session ranking deterministic.

---

## 8. ANTI-CHURN STABILITY

`MorningTradingPipelineService` использует `SIGNAL_STABILITY_OBSERVATIONS = 2`.

```text
1-е последовательное active observation → ARMED
2-е последовательное active observation → READY
trigger inactive → stability counter reset
READY + обычный transient retreat → READY
explicit invalidation → INVALIDATED
new_setup=True → новый lifecycle без старой стабильности
```

Stability не меняет SPOT ranking, candidate score, RS, setup detection или futures eligibility. Historical replay использует ту же границу.

---

## 9. FUTURES MAPPING BOUNDARY

Futures — только reference mapping выбранного SPOT-актива.

До `signal_state ∈ {READY, CONFIRMED}` futures mapping data очищаются из результата. После canonical READY/CONFIRMED mapping может быть показан как reference-only.

Дополнительные ограничения: direction должен совпадать с setup direction; trigger должен быть directional active; `days_to_expiry <= 3` исключается; futures не участвуют в SPOT eligibility, direction, RS, setup, readiness или ranking.

`futures_confirmation` всегда `NOT_APPLICABLE`; futures не подтверждают SPOT signal.

---

## 10. EVENT-RISK GATE

`moex_event_risk` остаётся жёстким SPOT eligibility gate и проверяется до candidate formation/mapping.

---

## 11. HISTORICAL REPLAY

Historical replay — `READ ONLY / NO ORDERS`.

Исторический SPOT candidate формируется и ранжируется до futures lookup. Futures не могут изменить historical SPOT eligibility или ranking.

`HistoricalUniverseReplayService` использует тот же network-free `lifecycle_state()` из canonical contract. Historical anti-churn parity повторяет live boundary, включая new-setup reset.

---

## 12. TEST ARCHITECTURE

Regression tests deterministic и не зависят от BCS refresh token, сети или live market-data.

Покрываются canonical lifecycle, trigger crossing/re-arm/invalidation, stability, setup quality, SetupEngine parity, live/historical parity, SPOT→futures boundary, event-risk, expiry, RS tie-break и независимость SPOT ranking от futures reference data.

CI проверяет фактический repository test inventory через `pytest -q Program`.

---

## 13. REPOSITORY HYGIENE / TEST INVENTORY — 27.08.2026

Обнаружен legacy-каталог `Program/tests/`. Его содержимое не было слепо удалено: четыре полезных набора regression coverage перенесены в канонический корень `Program/`:

- `test_futures_selection_and_market_universe.py`;
- `test_historical_candidate_ranker_service.py`;
- `test_moex_index_universe_service.py`;
- `test_spot_universe_service.py`.

После переноса старые копии из `Program/tests/` удалены. Production services не удалялись, поскольку по текущему inventory они являются частью архитектуры или используются существующими тестами/runners.

Также устранён единственный обнаруженный pytest collection warning: тестовый harness `TestableRadar` переименован в `RadarHarness`, поскольку pytest ошибочно пытался собирать helper-class с `__init__` как test class.

Локальная рабочая правка исторического теста сохранена в перенесённом canonical test: readiness/mapping fixtures теперь используют действительно активный trigger boundary (`spot_price == entry_trigger`).

---

## 14. VALIDATED CHECKPOINTS — 27.08.2026

### Canonical lifecycle hardening
Deterministic `WATCH → ARMED → READY → CONFIRMED`, directional crossing, terminal invalidation и explicit new-setup reset.

### Historical canonical boundary
Historical replay переведён на canonical lifecycle contract.

### Setup quality layer
Создан отдельный deterministic `SetupQualityService` с bounded structural scoring.

### SetupEngine quality integration
Quality интегрирована в SetupEngine как enrichment без изменения detection/lifecycle semantics.

### Live anti-churn
Введён двухнаблюдательный `ARMED → READY` gate.

### Historical/live stability parity
Historical replay повторяет live stability boundary и new-setup reset.

### Canonical futures mapping boundary
Финальный live pipeline gate не позволяет показать futures mapping до canonical `READY/CONFIRMED`.

### Repository CI inventory correction
GitHub Actions переведён на фактический repository inventory:

```text
python -m compileall -q Program
PYTHONPATH=Program python -m pytest -q Program
```

### Repository cleanup checkpoint — 27.08.2026
Legacy nested tests migrated into the canonical `Program/test_*.py` inventory, stale copies removed, pytest collection warning eliminated. No additional branch created.

---

## 15. RC UI / RUNTIME CHECKPOINT — 28.08.2026

### Git / source checkpoint

Подтверждено на локальном iMac:

```text
branch: main
HEAD: c495a93
origin/main: c495a93
working tree: clean
Python compile: OK
```

Commit `c495a93` — `Finalize Russian SPOT radar UI for RC`.

### Russian SPOT radar UI

Канонический UI `Program/watchlist_ui.py` содержит русские пользовательские формулировки:

- `SPOT-РАДАР ВОЗМОЖНОСТЕЙ`;
- `ОЦЕНКА ВОЗМОЖНОСТИ`;
- `СИЛА СЦЕНАРИЯ`;
- `РЕКОМЕНДАЦИЯ`;
- `ДЕНЬГИ И АКТИВНОСТЬ`;
- `ОТНОСИТЕЛЬНАЯ СИЛА`;
- `СЕТАП И ТРИГГЕР`;
- русские состояния готовности/подтверждения.

Отдельно зафиксировано важное ограничение: `ОЦЕНКА ВОЗМОЖНОСТИ` является детерминированным рейтингом модели, **а не статистической вероятностью исхода**. Нельзя представлять score как доказанную вероятность роста/падения без отдельной статистической валидации.

### SPOT money / activity отображение

UI показывает:

- SPOT цену;
- средний дневной оборот `₽×V`;
- текущий session `₽×V`;
- `₽×V/мин`;
- изменение цены;
- RS и RS score;
- локальные high/low;
- trigger level и trigger state.

Таким образом, оборот `price × volume` и относительная активность являются частью действующего SPOT radar contract и отображаются пользователю.

---

## 16. INSTALLED `.APP` ARCHITECTURE AUDIT — 28.08.2026

Установленный bundle:

```text
/Users/ilshatmac/Applications/Trader_7_12 Pro.app
```

Подтверждено:

```text
CFBundleName:                 Trader_7_12 Pro
CFBundleShortVersionString:  1.4
CFBundleVersion:             1.4
CFBundleIdentifier:          com.trader712.pro
CFBundleExecutable:          Trader_7_12 Pro
CFBundleDevelopmentRegion:  ru
Architecture:                Mach-O 64-bit x86_64
```

Дата изменения установленного `.app` на момент аудита: `2026-08-27 08:38:23`.

### Критически важная архитектура `.app`

`.app` не содержит отдельную копию Python-проекта. Bundle содержит launcher, который непосредственно обращается к каноническому рабочему каталогу:

```text
ROOT="/Users/ilshatmac/Documents/Trader_7_12"
export PYTHONPATH="$ROOT/Program"
exec /usr/bin/env python3 "$ROOT/Program/main.py"
```

Следовательно, `.app` и терминальный запуск используют **один и тот же исходный `Program` и один и тот же `Program/main.py`**, при условии запуска на этом iMac.

### BCS credentials path

Launcher использует macOS Keychain:

```text
macOS Keychain
 ↓
Trader_7_12 BCS Refresh Token
 ↓
BCS_REFRESH_TOKEN
 ↓
Program/main.py
 ↓
BCS
```

Ключ/refresh token не хранится в app bundle, Git repository или `Info.plist`.

Это является каноническим способом передачи BCS credential для `.app`.

### Что доказано и что ещё требует runtime-проверки

**Доказано:**

- `.app` существует;
- `.app` вызывает launcher;
- launcher использует `/Users/ilshatmac/Documents/Trader_7_12`;
- launcher выставляет `PYTHONPATH` на текущий `Program`;
- launcher запускает текущий `Program/main.py`;
- launcher извлекает BCS refresh token из macOS Keychain;
- source Git и `origin/main` совпадали на `c495a93`;
- `Program` успешно проходит Python compile.

**Отдельно требуется эксплуатационно подтвердить:**

- успешную авторизацию БКС именно при запуске `.app`;
- успешное получение live market data через `.app`;
- соответствие фактического результата `.app` терминальному запуску при открытом рынке.

Рынок 27.08.2026 на момент соответствующей проверки уже был закрыт, поэтому отсутствие live scan результата в `.app` в этот момент не является доказательством неисправности.

### Code signing

На момент аудита `codesign -dv --verbose=2` сообщил:

```text
code object is not signed at all
```

Это не является функциональным дефектом текущего внутреннего RC и не меняет Python/BCS/data-path архитектуру. Подписание bundle является отдельным release/distribution hardening уровнем.

---

## 17. RC RUNTIME DATA CONTRACT

Канонический runtime data path:

```text
`.app` / terminal
 ↓
Keychain / BCS_REFRESH_TOKEN
 ↓
BCS authorization
 ↓
BCS instruments / market data
 ↓
SPOT universe
 ↓
SPOT price + volume
 ↓
price × volume / activity
 ↓
market benchmark
 ↓
RS
 ↓
H1 / M5 structure
 ↓
setup
 ↓
trigger
 ↓
stability
 ↓
SPOT opportunity score
 ↓
TOP SPOT watchlist
 ↓
futures mapping only
```

Runtime логика не должна подменять отсутствующие обязательные market-data фиктивными значениями. В частности, `RS_UNAVAILABLE` должен оставаться недоступным состоянием, а отсутствие trigger/levels должно отображаться как отсутствие уровня, а не как искусственный trigger.

Цель эксплуатации: показывать пользователю прежде всего инструменты, в которых одновременно наблюдаются существенный `price × volume`, повышенная относительно нормы активность, направленное движение и значимое отклонение от benchmark. Такой инструмент является более интересным кандидатом для дальнейшего самостоятельного анализа, но сам radar не утверждает гарантированный исход.

---

## 18. CURRENT RC STATUS

**Статус:** Release Candidate / эксплуатационная валидация продолжается.

### Уже пройдено

- canonical SPOT-first architecture;
- money/activity layer;
- directional trend;
- RS vs market benchmark;
- H1/M5 setup;
- trigger semantics;
- anti-churn stability;
- readiness/confirmation lifecycle;
- setup quality;
- deterministic ranking;
- event-risk gate;
- historical replay parity;
- futures mapping boundary;
- repository cleanup;
- deterministic test architecture;
- Russian RC UI;
- Git/GitHub synchronization;
- `.app` launcher architecture audit;
- Keychain credential architecture audit.

### Осталось для финального эксплуатационного RC sign-off

1. На открытом рынке запустить `.app` и подтвердить успешную авторизацию БКС.
2. Выполнить live scan через `.app`.
3. Подтвердить, что получаются реальные данные БКС.
4. Сверить ключевые поля `.app` с терминальным запуском на том же market snapshot.
5. Выполнить полный repository regression command после последнего RC commit.
6. При необходимости отдельно проверить/подготовить code signing для распространяемого macOS bundle.

До прохождения этих пунктов `.app` считается **архитектурно подтверждённым, но runtime live-data path ещё не полностью подписан как финально validated**.

---

## 19. RELEASE / WORKFLOW RULE

После каждого законченного уровня:

1. изменения сохраняются в GitHub `main`;
2. commit фиксируется;
3. `PROJECT_PASSPORT.md` обновляется;
4. compile/regression checks проходят на локальном iMac;
5. пользователь делает один `git pull --ff-only`;
6. reinstall требуется только если изменены app bundle/launcher/icon или другой локально собираемый компонент.

**Канонический паспорт:** `Docs/PROJECT_PASSPORT.md`.  
**Рабочая ветка:** только `main`.  
**Дополнительные ветки:** не создаём.
