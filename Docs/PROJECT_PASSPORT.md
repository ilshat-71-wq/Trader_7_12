# TRADER_7_12 PRO — PROJECT PASSPORT

**Дата актуализации:** 01.10.2026  
**Репозиторий:** `Trader_7_12`  
**Ветка:** `main` — единственная рабочая ветка  
**Статус:** production-oriented read-only market-information scanner  
**Radar pipeline:** D1-first production chain (current implementation)  
**Futures OI scanner:** current production implementation  
**Последний функциональный commit:** `fb3a67fd7d03af40f5c0c83e9f54af1297d8a701` — `Test FINAL Radar futures confirmation display`  
**Текущий GitHub `main` HEAD:** `22f16092cb52c14d9f8aedd8e623e2b439643836`  
**Последний локально подтверждённый regression suite:** `197 passed, 1 warning` (30.09.2026)  
**Последний regression-test commit:** `fb3a67fd7d03af40f5c0c83e9f54af1297d8a701`  
**Последний build-infrastructure commit:** `f2e0aff5bf5034aa483cb81b3834640735feb382`  
**Архитектура клиента:** одно и только одно macOS-приложение `Trader_7_12 Pro.app`.

## 0.3 Realtime confirmation checkpoint — 23.09.2026

Сохранена рабочая точка после расширения realtime-подтверждения SPOT market map.

Последний realtime commit:

`937a578c — Expand realtime confirmation to top SPOT market-map rows`

### Realtime
- перед каждой новой WebSocket-сессией выполняется повторная авторизация/обновление токена, чтобы reconnect не зависел от устаревшего access token;
- futures realtime candidate rows сохраняют authoritative BCS `classCode` из contract metadata;
- SPOT realtime подписывается на ограниченный TOP-30 текущего `market_map`, отсортированный по `abs(relative_strength)`, а не на весь universe;
- цель слоя — дать BOOK/TAPE/FLOW RT подтверждение тем же текущим сильным/слабым market-map rows, которые видит оператор;
- scanner calculations, qualification, ranking, market-map source и BCS market-data semantics не изменены;
- локально подтверждено: `149 passed, 1 warning`.

### Acceptance
После pull на iMac обязательна локальная проверка: pytest → build → open единственного `Trader_7_12 Pro.app`. До фактического успешного build на iMac статус приложения не считать подтверждённым.

## 0.2 UI / Diagnostics checkpoint — 23.09.2026

Сохранена текущая рабочая точка после SPOT market-map и UI-диагностики.

Последовательность последних UI-коммитов:

```
d086abb5 — Fix SPOT market map diagnostics entry
58893dd7 — Compact diagnostics and improve global copy action
0ac841c3 — Compact Futures OI diagnostics and return copy status
613dbb4 — Add professional copy action to Morning Radar
```

### Диагностика
- DIAGNOSTICS больше не выводит полный `market_map` и внутренние массивы.
- Сохраняется компактный операторский паспорт: status/session/regime, coverage, liquidity, selection, market-map counts, skips и timings.
- Полный `market_map` остаётся в scanner diagnostics для вкладок STRONGER / WEAKER и не удалён из backend.

### Копирование
- Основная кнопка `COPY` работает с активным представлением.
- Таблицы поддерживают `⌘C / Ctrl+C`, выделение строк и контекстное меню.
- DIAGNOSTICS копируется как компактный текстовый паспорт.
- Futures OI возвращает статус копирования.
- Morning Radar получил отдельную профессиональную кнопку `COPY`, копирующую summary + таблицу + OI summary.
- После копирования UI показывает `COPIED ✓`.

### Важное правило
UI-изменения не меняют scanner calculations, qualification, ranking, market-map source или BCS market-data semantics.

Текущая точка должна сначала пройти локальные `py_compile` / `pytest` и macOS build после синхронизации рабочей машины.


## 0.4.2 FINAL RADAR correction — 01.10.2026

### Final Radar
- Исправлено представление FUTURES-кандидата в FINAL RADAR: собственный фьючерс теперь отображается как подтверждённый Futures-контур с контрактом и его текущей вероятностью, вместо misleading FUTURES —.
- Для FUTURES-кандидата это не новый сигнал и не новый сканер: FINAL использует уже рассчитанные signal / signal_probability того же Futures OI / Money Flow результата.
- RT-порог 55 не ослаблялся и не изменялся.
- Realtime FINAL продолжает использовать реальные BOOK/TAPE/FLOW snapshot того же тикера и среднее доступных компонентов при наличии минимум двух компонентов.
- Добавлен regression test: для NGV6 при BOOK 56 / TAPE 100 / FLOW 78 FINAL RT должен быть 78.0, а собственный Futures должен быть CONFIRMED с контрактом NGV6.
- Важно: ранее наблюдавшийся FINAL RT 41 не был доказан как ошибка расчёта. По текущему коду это значение соответствует последнему realtime snapshot, который FINAL успел получить в момент отображения. При последующем живом snapshot NGV6 = 56/100/78 FINAL должен пересчитать RT в 78.
- Поэтому порог 55 не менялся: при актуальном NGV6 realtime 78 > 55.

### Git
- 55874c791e888260e7ef47c6f402f92d92adac93 — исправление FUTURES-представления в FINAL RADAR.
- fb3a67fd7d03af40f5c0c83e9f54af1297d8a701 — regression test для собственного Futures confirmation.

## 0.4.1 Current verified checkpoint — 01.10.2026

### Git / benchmark fix
- GitHub `main` = `15273355d530b6d4f211725faf6c4a912881305f`.
- Exact production fix: `BENCHMARKS = ("IMOEX", "IRUS2")`.
- Previous incorrect production benchmark was `IMOEX2`; real BCS index catalog is `IMOEX / INDX`.
- No new scanner or architecture was introduced.

### Real BCS verification
- BCS authorization: successful.
- Real `IMOEX / INDX` D1 history: 28 candles returned.
- `DailyTrendProfileService` version 2.2 was tested directly with real TQBR D1 candles and real IMOEX D1 candles.
- Confirmed real D1 qualified examples:
  - ARSA: LONG, 3 days, +16.56%, STRONGER, qualified=True.
  - OZON: LONG, 3 days, +3.44%, STRONGER, qualified=True.
  - LKOH: LONG, 3 days, +3.05%, STRONGER, qualified=True.
  - GMKN: SHORT, 3 days, -2.09%, WEAKER, qualified=True.
- This proves the D1 → IMOEX relative-strength qualification layer works with real BCS data.

### Production Radar runtime state
- `MarketAttentionScannerService.scan()` was tested at 01:13 MSK while `MarketSessionService` reported `CLOSED`, `market_open=False`, `session_start=None`.
- Therefore `scan() -> []` at that time is not treated as a Radar failure.
- The next required proof is one production scan during an open trading session, followed by H1 → M5 → M1 verification.
- Do not manufacture an off-session scan or weaken session/data gates to obtain rows.

### Realtime
- Latest technically confirmed realtime state remains: 100 subscribed instruments, BOOK 100/100, TAPE 100/100, with BCS protocol acknowledgements.
- Realtime remains confirmation only; it must not rewrite D1/M5 direction semantics.

### Local working tree warning
- Local iMac currently has an uncommitted change: `Program/test_daily_trend_profile_service.py`.
- Do not commit or discard it blindly.
- GitHub `main` itself is clean at `1527335`; resolve the local test-file change deliberately before the next local sync/build.

### Required next live acceptance
1. Open trading session.
2. Run production `MarketAttentionScannerService.scan()`.
3. Confirm real D1-qualified rows and their D1 directions reach production Radar.
4. Confirm H1 alignment.
5. Confirm M5/M1 entry chain.
6. Run full app check only after the real production scan is verified.


## 0.4 New-chat recovery protocol — CANONICAL

**Purpose:** a new ChatGPT chat must recover the project from GitHub and this canonical passport. Conversational memory is auxiliary only.

### Source of truth
1. GitHub repository: `ilshat-71-wq/Trader_7_12`
2. Working branch: `main` — the only working branch.
3. Canonical project passport: `Docs/PROJECT_PASSPORT.md`
4. Current code on `main` is authoritative for implementation details.
5. Verified local tests, live checks and build output are authoritative for acceptance claims.

### Mandatory local synchronization
```bash
cd ~/Documents/Trader_7_12 && \
git fetch origin && \
git switch main && \
git pull --ff-only origin main && \
echo "=== SYNC CHECK ===" && \
git status --short --branch && \
git log -1 --oneline
```

Expected: `main` tracks `origin/main`, working tree clean, local HEAD equals GitHub `main`.

### Mandatory project workflow
```
change
→ tests
→ real check
→ commit main
→ update PROJECT_PASSPORT.md
→ push main
→ local pull
→ build
→ open the single Trader_7_12 Pro.app
→ app check
```

### Current verified checkpoint — 28.09.2026

**GitHub / source**
- Current source before this passport-only update: `23cf3a3bf3f2e14ca0704f62ba10586a039ed4db`.
- Final Radar operator diagnostics are implemented in `Program/services/final_radar_service.py` and `Program/final_radar_ui.py`.
- Final Radar still uses the existing three-consecutive-scan confirmation model; the diagnostics patch does not weaken or alter scoring/gates.
- Final Radar UI header is aligned to its 11 data columns.
- Scan animation repaint cadence is 200 ms (5 fps), commit `7999b459efa594672c888afb41d15484efe60c63`; no scanner/data/realtime semantics were changed.

**Tests**
- Local full suite after pull: `186 passed, 1 warning in 2.05s`.
- The only warning is the Python 3.14 / pytest-asyncio deprecation warning for `asyncio.get_event_loop_policy`.

**macOS application**
- Build completed successfully from source commit `23cf3a3bf3f2e14ca0704f62ba10586a039ed4db`.
- Bundle version: `2.4.3`.
- Artifact: `dist/Trader_7_12 Pro.app`.
- Signed install: `~/Applications/Trader_7_12 Pro.app`.
- Packaging: PyInstaller onedir + macOS `.app`.
- Signing: ad-hoc.
- One desktop application only.

**Measured GUI performance**
- Running built app for about 11 minutes: `20.2% CPU`, `1.8% MEM`, RSS `222272 KB`.
- Sampling still shows `QPainter::drawEllipse` as the dominant GUI paint activity, while `QTableWidgetItem/setData/setBackground` are not dominant in the captured sample.
- Current 200 ms animation cadence is accepted; do not optimize further without new measured evidence.

**Latest real market evidence**
- Last observed live scan: 28.09.2026, EVENING, REGIME DOWN.
- SPOT: Universe 261, Analyzed 254, Coverage 97.3%, Liquidity passed 105, D1 qualified 1, Directional qualified 0, Strict 0, Watch 20, Market map 254.
- Futures: Contracts 8/8 OI, Money Flow was `NO_DATA` after market close, realtime subscriptions were acknowledged; one observed closed-session run showed 8 instruments with BOOK 8/8 and TAPE 8/8.
- This closed-session Money Flow `NO_DATA` is not treated as a production failure.
- `No diagnostics available` was observed after market close; no conclusion is drawn about Final Radar runtime until a live trading-session scan produces strict candidates/diagnostics.

**Final Radar acceptance state**
- No current strict SPOT candidate was available in the closed-session scan, so there was no `1/3`, `2/3` or `3/3` confirmation to validate.
- Next real acceptance is during an open trading session: verify `Strict` candidates and the intended `1/3 → 2/3 → 3/3` chain, plus realtime and Futures gates.
- Do not weaken gates because of weekend/evening/missing-data conditions.

### Passport update rule
After every material project change, update this same canonical passport. Do not create a second project passport or parallel status MD.

### Important things that must not be changed without evidence
- REAL DATA ONLY; no synthetic values, tickers, classCodes, liquidity, OI or prices.
- No futures-as-SPOT substitution.
- No order execution, position sizing, SL/TP execution or portfolio management.
- Do not weaken coverage, liquidity, D1/M5, Futures OI, Money Flow, realtime or Final Radar gates merely to obtain a candidate.
- Realtime BOOK/TAPE/FLOW RT must remain an additional confirmation layer and must not rewrite D1/M5 signal semantics.
- Keep one coherent macOS application.
- Any performance optimization must preserve data/scoring/realtime semantics and be measured before/after.

### Next concrete step
Because this passport update creates a new GitHub `main` commit, the iMac must pull that final passport commit and rebuild once more. Then the bundle source commit and the canonical passport will be aligned to the same GitHub `main` state.

### Standing project rule
**A new chat starts from GitHub `main` + this passport, not from memory alone.**

## 1. Назначение

Trader_7_12 Pro — единое macOS read-only приложение для объективного мониторинга текущего рынка. Оно анализирует реальные BASE/SPOT-инструменты, D1/M5, относительную силу к рынку, ликвидность, денежный поток, acceleration и отдельно показывает Futures OI-контекст.

Программа не выставляет заявки, не управляет позициями, не рассчитывает размер позиции, SL/TP и не исполняет сделки.

## 2. Главный принцип

**Relative Strength vs Market**, а не угадывание абсолютного направления цены.

```text
РЫНОК РАСТЁТ → ищем сильные относительно рынка → LONG candidates
РЫНОК ПАДАЕТ → ищем слабые относительно рынка → SHORT candidates
NEUTRAL → строгий directional candidate не создаём
```

```text
RS = PRICE Δ% − IDX Δ%
```

Benchmark: `IMOEX` / `INDX`. `IMOEX2` не используется в production Radar. Meaningful RS threshold: `0.10 pp`.

## 3. BASE universe

```text
ALL MOEX TQBR STOCKS
GOLD
OIL
GAS
USDRUB
```

Только реальные BCS BASE/SPOT.

Нельзя:
- заменять SPOT фьючерсом;
- создавать synthetic quote/value/classCode/ticker;
- ставить 0 при отсутствии данных;
- считать отсутствие данных отсутствием движения.

GOLD → `GLDRUB_TOM` при наличии real BCS SPOT. USDRUB → real SPOT. OIL/GAS → только real BASE/SPOT; иначе `UNAVAILABLE`/diagnostic.

## 4. Radar pipeline

```text
BASE/SPOT
→ D1 structure
→ D1 RS vs IMOEX
→ current M5
→ session price/change
→ session ₽×V
→ ₽×V/min
→ recent 15m flow
→ liquidity gates
→ acceleration
→ current RS vs benchmark
→ market regime
→ qualification
→ attention ranking
```

## 5. D1 quality

`DailyTrendProfileService` deterministic and without network.

STRONG:
- выбранные D1 свечи зелёные;
- High строго растёт;
- Low строго растёт;
- актив сильнее IMOEX2 в каждом сопоставленном дне.

WEAK — зеркально. Смешанная структура не получает STRONG/WEAK.

D1 — primary directional quality gate. Current intraday RS is confirmation, not D1 direction.

## 6. Liquidity / flow

Hard gates:

```text
MIN_MONEY_PER_MINUTE        = 8 000 ₽/min
MIN_RECENT_MONEY_PER_MINUTE = 5 000 ₽/min
```

Оба обязательны для strict candidate.

Acceleration:

```text
recent complete 15m pace / previous complete 15m pace - 1
```

Нужно 3 M5 candles в каждом полном окне и positive previous flow; иначе acceleration = 0.

Attention score:

```text
45% recent ₽×V/min
25% session ₽×V
20% session ₽×V/min
10% acceleration percentile
```

## 7. Coverage / missing data

Production M5 coverage minimum: **80%**. Ниже 80% → `INSUFFICIENT_COVERAGE`.

Missing real data всегда остаётся missing/UNAVAILABLE/diagnostic. Отсутствие данных нельзя превращать в нули или synthetic values.

## 8. UI

Единое приложение `Trader_7_12 Pro.app`.

```text
RADAR
FUTURES OI
DIAGNOSTICS
SETTINGS
```

Основная Radar table:

```text
# | Ticker | Role | D1 | D1-RS | IDX Δ% | Price Δ% | RS | ₽/min | DAY ₽ | 15m | Accel | Score
```

UI не изменяет расчёты, qualification, ranking или порядок результатов.

## 9. Futures OI

Источник:

```text
MOEX RFUD marketdata / securities
```

Primary OI — реальный MOEX RFUD marketdata по реальному SECID. FUTOI — supplemental.

Front policy:

```text
ACTIVE → NON-EXPIRED → OI > 0 → NEAREST EXPIRY → FRONT
```

Regimes:

```text
↑ price + ↑ OI → NEW_POSITION_BUILDING_UP
↑ price + ↓ OI → SHORT_COVERING
↓ price + ↑ OI → NEW_POSITION_BUILDING_DOWN
↓ price + ↓ OI → LONG_LIQUIDATION
```

Futures liquidity — только `VALTODAY`. Никаких `PRICE × VOLUME`, synthetic VALUE или ручного проталкивания тикеров в TOP20.

## 10. Futures BASE mapping

Canonical mappings:

```text
GZ      → GAZP
SR      → SBER
RI      → RTS
SI      → USDRUB
EU      → EURRUB
CR/CNY  → CNYRUB
GD      → GLDRUB_TOM
MX/MM   → IMOEX
IMOEXF  → IMOEX
```

Examples:

```text
SIU6     → USDRUB
CRU6     → CNYRUB → CNYRUB_TOM/CETS
MXU6     → IMOEX → IMOEX/INDX
GDU6     → GLDRUB_TOM → GLDRUB_TOM/CETS_MTL
IMOEXF   → IMOEX/INDX
CNYRUBF  → CNYRUB_TOM/CETS
USDRUBF  → USDRUB
EUU6     → EURRUB → EUR_RUB__TOM/CETS
RIU6     → RTS
SRU6     → SBER/TQBR
GZU6     → GAZP/SMAL
SFU6     → SPY/QMEBLCK
NAU6     → QQQ/SPBXM
EDU6     → ED/SPBXM
RBZ6     → RGBI/INDX
```

MIX и IMOEXF не объединяются в один futures product: общий economic underlying не означает одинаковый контракт.

BCS policy:
1. canonicalize futures family;
2. determine economic underlying;
3. preferred catalog lookup;
4. real BCS `get_instruments_by_tickers()`;
5. accept only real BCS records;
6. use real ticker + real classCode;
7. normalize aliases only when matching an actual returned record;
8. quote only accepted real ticker/classCode;
9. no synthetic fallback.

Preferred catalog pairs:

```text
USDRUB      → USDRUB_TOM / CETS
EURRUB      → EURRUB_TOM / CETS
CNYRUB      → CNYRUB_TOM / CETS
GLDRUB_TOM  → GLDRUB_TOM / CETS_MTL
IMOEX       → IMOEX / INDX
RTS         → RTS / INDX
RGBI        → RGBI / INDX
SBER        → SBER / TQBR
GAZP        → GAZP / SMAL
QQQ         → QQQ / SPBXM
SPY         → SPY / QMEBLCK
```

Catalog is lookup preference only; live BCS metadata is source of truth.

### 10.1 Authoritative BCS base-asset metadata evidence — 21.09.2026

Для dated futures связь с BASE/SPOT должна в первую очередь браться из реальной карточки futures, возвращённой BCS POST /api/v1/instruments/by-tickers в режиме raw (resolve_underlying=False). В карточке BCS для commodity futures может отсутствовать вложенный объект baseAsset, но присутствуют поля:

    baseAssetSecurityClassCode
    baseAssetSecuritySecCode

Фактически проверено через авторизованный BCS API 21.09.2026:

    NGU6 → baseAssetSecurityClassCode = FEG
           baseAssetSecuritySecCode   = NGas1026
           baseAsset = "Природный газ"

    NGZ6 → baseAssetSecurityClassCode = FEG
           baseAssetSecuritySecCode   = NGas1026
           baseAsset = "Природный газ"

    SIZ6 → BCS /instruments/by-tickers не возвращает карточку SIZ6.
    USDRUBF → baseAssetSecurityClassCode = CETS_FX
              baseAssetSecuritySecCode   = USD000SMALL

    USD000SMALL → реальная BCS карточка:
                  ticker = USD000SMALL
                  instrumentType = CURRENCY
                  primaryBoard = CETS_FX
                  boards.classCode = CETS_FX
                  displayName = "Доллар США"
                  type = "Валютная пара"
                  settleCode = T+1
                  tradingCurrency = RUB

    USD000SMALLF / USD000SMALL_TOM / USD000SMALL_TOD → BCS records: 0

Зафиксированное правило: USD000SMALL / CETS_FX — реальный BCS BASE/SPOT-инструмент USD/RUB и может использоваться как источник market data для USD/RUB после успешного получения его реальных candles/quote. USDRUBF — perpetual FUTURES и никогда не является заменой BASE/SPOT; его карточка используется только как источник доказательства связи USD000SMALL.

Зафиксированное правило для commodities: если BCS futures card содержит baseAssetSecuritySecCode + baseAssetSecurityClassCode, эта пара является authoritative base-asset reference. Нельзя заменять её ручным тикером, perpetual futures или синтетическим classCode.

Реализовано в scanner v2.7.20: parser _base_asset_reference() читает baseAssetSecuritySecCode + baseAssetSecurityClassCode напрямую из futures card. Для NGU6/NGZ6 это даёт FEG / NGas1026. Для SIZ6/USDRUB связь теперь может быть подтверждена через реальный USD000SMALL / CETS_FX; USDRUBF остаётся запрещённым как BASE/SPOT source. Следующий live-шаг — проверить реальные USD000SMALL M5 candles 07:00→NOW и повторить Futures OI diagnostics.

## 11. Mapping status — CURRENT P0

Mapping has materially improved but is **not yet production-complete**.

Historical diagnostics included:

```text
underlying_requested = 195
underlying_class_codes = 48
underlying_class_code_missing = 147
underlying_metadata_lookup_batches = 2
underlying_metadata_lookup_records = 148
underlying_exact_matches = 48
underlying_semantic_matches = 0
```

The 147 missing entries must be classified, not blindly treated as broken BASE mappings:

```text
A. supported BASE instruments requiring BASE Δ%
B. futures-only instruments outside BASE
C. genuinely unresolved BCS mappings
```

Next mapping milestone: honest classification of all unresolved entries and production-quality supported BASE mapping with real BCS metadata only.

## 12. BCS/API architecture

- process-wide singleton read-only `BCSAPI`;
- bounded candle timeout/retry/concurrency;
- candle cache TTL about 30s;
- global candle concurrency currently 4;
- shared process-wide metadata cache;
- SPOT universe uses shared metadata cache;
- futures/index mapping partially reuses shared metadata;
- exact ticker-set cache plus per-ticker BCS metadata cache with the same 300s TTL;
- overlapping ticker requests reuse already-known real BCS cards instead of repeating `/instruments/by-tickers`;
- returned records are cached under their real, unambiguous BCS aliases;
- no change to BCS network concurrency or market-data semantics.

Remaining performance architecture task: add in-flight deduplication only if measured concurrent overlap still justifies it; do not increase network concurrency blindly.

## 13. Performance

Radar version: `2.5.1`.

D1 profiles use bounded parallelism:

```text
D1_MAX_WORKERS = 6
```

Diagnostics include:

```text
universe
benchmark
benchmark_d1
m5
d1
calculation
total
```

stored as `timings_seconds`.

Workflow:

```text
1. obtain real timings_seconds from one complete scan;
2. identify dominant phase;
3. fix measured bottleneck only;
4. regression test;
5. measure again.
```

Do not weaken market criteria for speed.

## 13.1 Latest measured Cloud scan — 22.09.2026

Before the per-ticker metadata cache optimization:

```text
CLOUD SCAN TIMING: RADAR=92.187s FUTURES_OI=2.696s MONEY_FLOW=1.866s SNAPSHOT=0.002s TOTAL=96.751s

RADAR BREAKDOWN: UNIVERSE=34.266s BENCHMARK=0.185s BENCHMARK_D1=0.118s M5=29.367s D1=28.181s CALCULATION=0.013s TOTAL=92.186s

UNIVERSE BREAKDOWN: SPOT_LOAD=4.798s MACRO_METADATA=29.467s FILTERING=0.001s ASSEMBLY=0.000s TOTAL=34.265s
```

The measured bottleneck was repeated BCS instrument metadata lookup, not candle HTTP failures. M5 and D1 diagnostics reported zero HTTP errors in that run. This measurement is the baseline for validating commit `272a9c1`.

## 14. HTTP / resilience

- HTTP/SSL failure is not equal to no trading;
- bounded retry;
- coverage/diagnostics reflect degradation;
- Futures OI uses common `RequestHelper` with TLS/retry;
- no ad-hoc urllib client for OI.

## 15. Calendar

```text
MORNING  06:50–09:00 MSK
MAIN     09:00–19:00 MSK
EVENING  19:00–23:50 MSK
DSWD     09:50–19:00 MSK
```

Weekend does not automatically substitute Friday data. On Sunday 13.09.2026 state is `MARKET_CLOSED`; current BASE Δ% is unavailable without a current session window. Futures cannot fill SPOT.

## 16. Sound / scan workflow

Sound settings are in SETTINGS.

User-tested status on 13.09.2026:
- final completion melody **WORKS**;
- it plays after the complete RADAR + Futures OI workflow;
- start melody is **NOT CONFIRMED / NOT HEARD**.

Latest sound commit:

```text
89d63cd — Fix completion sound to fire after full scan
```

This is a UI/audio issue, not a market-data calculation issue.

## 17. macOS build / signing — UPDATED 22.09.2026

Build script:

```text
scripts/build_mac_app.sh
```

Production client:

```text
dist/Trader_7_12 Pro.app
```

There is exactly **one desktop application**. We do not create separate applications for Radar, Futures OI, Diagnostics, Cloud, or any other subsystem. These are functional areas of the same `Trader_7_12 Pro.app`.

The Cloud Market Data Engine is a backend service, not a second desktop application.

PyInstaller: onedir + macOS `.app` BUNDLE. Local production signing is ad-hoc.

The build script was changed in commit `f2e0aff5bf5034aa483cb81b3834640735feb382` to stage PyInstaller output outside the affected project/File Provider metadata tree, perform controlled final signing/verification, and then place the single production application in `dist`.

Required final verification:

```text
=== APP BUILD OK ===
Code signing: ad-hoc verified
```

The source checkpoint `23cf3a3` has already been built and verified locally. This passport-only commit now requires one final pull/build so the bundle source commit and canonical passport commit are synchronized.

## 18. Tests

Latest confirmed local regression:

```text
186 passed, 1 warning in 2.05s
```

Previous confirmed local regression before the realtime checkpoint:


```text
121 passed in 1.21s
```

The build script also ran:

```text
121 passed in 1.34s
```

Standard verification:

```bash
cd ~/Documents/Trader_7_12 && \
git pull --ff-only origin main && \
python3 -m pytest -q Program && \
./scripts/build_mac_app.sh
```

## 19. Read-only boundary

```text
NO ORDER EXECUTION
NO BUY/SELL COMMAND
NO POSITION SIZE
NO SL/TP EXECUTION
NO PORTFOLIO MANAGEMENT
```

## 20. Current priorities — STRICT ORDER

### P0 — Final iMac synchronization after passport commit
- pull the current `main`;
- build the single `Trader_7_12 Pro.app`;
- open that same application;
- inspect the complete single-window client: Radar, Futures OI, Diagnostics, Settings;
- verify Cloud status and data refresh presentation.

### P1 — Cloud API / multi-client validation
- `/health`;
- `/v1/status`;
- `/v1/snapshot`;
- `/v1/stream`;
- snapshot version increments;
- last-good snapshot survives failed refresh;
- concurrent `POST /v1/scan` is serialized;
- multiple WebSocket clients receive the same snapshot;
- clients do not create additional BCS scans.

### P2 — UI semantics / polish
Before changing calculations, verify the meaning and presentation of:
- `D1-RS`;
- `Score`;
- `Role`;
- `SIGNAL`;
- `PROB`;
- `FLOW`;
- `ACTION`;
- `ZONE`.

Keep strict candidates and WATCH candidates visually distinct. Keep FLOW, ACTION and final SIGNAL as separate concepts.

### P3 — Measured performance / mapping only where evidence requires it
- do not change stable M5/D1 candle settings without measured evidence;
- preserve the working metadata cache;
- preserve real-data-only mapping;
- classify remaining unavailable BASE mappings honestly;
- measure every optimization before/after.

## 21. Definition of professional completion

Before calling the project production-ready:

- supported BASE mapping materially complete and verified against real BCS metadata;
- unresolved mappings honestly classified;
- no synthetic fallback;
- full scan speed measured and predictable;
- repeated overlapping metadata requests deduplicated; in-flight dedupe remains optional and measurement-driven;
- M5/D1 access cached safely;
- coverage/diagnostics truthful;
- Futures OI uses real RFUD/OI/VALTODAY;
- Radar uses true relative strength vs market;
- regression suite green;
- macOS build green and ad-hoc signature verified;
- UI remains one coherent professional application; there is exactly one desktop application and all functional areas live inside it.

## 22. Non-negotiable rules

```text
REAL DATA ONLY
NO SYNTHETIC VALUES
NO FUTURES AS SPOT SUBSTITUTE
NO FAKE CLASS CODES
NO FAKE TICKERS
NO FAKE LIQUIDITY
NO ORDER EXECUTION
NO PORTFOLIO MANAGEMENT

NEVER RESTART THE PROJECT
NEVER SPLIT INTO MINI-SCANNERS
NEVER CREATE EXTRA APPLICATIONS OR UNNECESSARY ARCHITECTURE LAYERS

ONE MACOS APP ONLY — `Trader_7_12 Pro.app`
```
