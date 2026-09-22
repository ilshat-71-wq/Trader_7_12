# TRADER_7_12 PRO — PROJECT PASSPORT

**Дата актуализации:** 22.09.2026  
**Репозиторий:** `Trader_7_12`  
**Ветка:** `main` — единственная рабочая ветка  
**Статус:** production-oriented read-only market-information scanner  
**Radar pipeline:** 2.5.1  
**Futures OI scanner:** 2.7.20  
**Последний функциональный commit:** `272a9c1943a78bb9216fd4be7bc48498c89c9ab7`  
**Последний regression-test commit:** `42c62f446a7d28240c68123aca8fe2f57e575bf0`  
**Последний build-infrastructure commit:** `f2e0aff5bf5034aa483cb81b3834640735feb382`

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

Benchmark: `IMOEX2`; `IRUS2` — fallback только если IMOEX2 unavailable/unfit. Meaningful RS threshold: `0.10 pp`.

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
→ D1 RS vs IMOEX2
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

D1 — quality/context gate; он не подменяет current relative-strength logic.

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

## 17. macOS build / signing — UPDATED 13.09.2026

Build script:

```text
scripts/build_mac_app.sh
```

Application:

```text
dist/Trader_7_12 Pro.app
```

PyInstaller: onedir + macOS `.app` BUNDLE. Local production signing is ad-hoc.

### Signing incident and root cause

A PyInstaller build completed packaging but BUNDLE signing failed with:

```text
resource fork, Finder information, or similar detritus not allowed
```

Diagnostics proved:

```text
source Python.framework → no relevant xattr output
source PySide6 → no relevant xattr output
build/ → clean

dist/ → contaminated
```

The generated `dist` tree contained `com.apple.FinderInfo` and `com.apple.fileprovider.fpfs#P` on nested Python/PySide6 frameworks. No `._*` AppleDouble files and no `com.apple.ResourceFork` were found.

Conclusion: metadata is introduced in the generated distribution tree during/around PyInstaller BUNDLE construction under the project filesystem. Cleaning the finished `.app` after PyInstaller is too late because PyInstaller itself attempts BUNDLE signing before post-build cleanup.

### Build fix

Commit:

```text
f2e0aff5bf5034aa483cb81b3834640735feb382
```

The build script was changed to stage PyInstaller output outside the affected project/File Provider metadata tree, perform controlled final signing/verification, and only then place the production `.app` in `dist`.

Required final verification:

```text
=== APP BUILD OK ===
Code signing: ad-hoc verified
```

**Important:** the new build has NOT yet been confirmed successful by a real local build as of this passport update. Do not claim build green until the user runs the updated script and receives `=== APP BUILD OK ===`.

## 18. Tests

Latest confirmed local regression before the build-fix validation:

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

### P0 — Mapping correctness
- classify all unresolved underlying mappings;
- distinguish BASE-required from futures-only;
- verify real BCS ticker/classCode pairs;
- improve supported BASE coverage;
- preserve `UNAVAILABLE` when real source is absent;
- add regression tests for repaired mapping families.

### P1 — Scan speed
- use `timings_seconds` to identify bottleneck;
- validate the new overlapping per-ticker metadata cache against a complete live scan; add in-flight dedupe only if concurrent overlap remains measurable;
- eliminate repeated full instrument metadata downloads;
- add safe history/session candle cache where justified;
- keep bounded concurrency and BCS network safety;
- measure every optimization before/after.

### P2 — Diagnostics / acceptance
- make mapping coverage honest and explicit;
- expose timing phases clearly;
- preserve truthful missing-data states;
- keep Futures OI and money-flow sources explicit.

### P3 — UI / audio polish
- confirm/fix start scan melody;
- keep visualization light, clear and fast;
- preserve one coherent single-window application.

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
- UI remains one coherent professional application.

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
```
