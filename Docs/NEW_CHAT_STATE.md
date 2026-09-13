# TRADER_7_12 PRO — NEW CHAT STATE / HANDOFF

**Состояние на:** 13.09.2026  
**Repo:** `ilshat-71-wq/Trader_7_12`  
**Branch:** `main`  
**Latest infrastructure commit:** `f2e0aff5bf5034aa483cb81b3834640735feb382`  
**Latest passport commit:** `4ea447bcbd6371adef0a315bf17a5876d2d08238`  
**Previous functional/sound commit:** `89d63cd807afcbb28d0ca35d9e5f2022ce498532`

## 0. Готовая инструкция для нового чата

> Продолжаем существующий проект TRADER_7_12. Это НЕ новый проект. Прочитай `Docs/PROJECT_PASSPORT.md` и `Docs/NEW_CHAT_STATE.md` в GitHub и продолжай строго с текущего состояния. Я — автор идеи и требований, ты — архитектор и технический руководитель. Не создавай новые приложения, мини-сканеры или лишние архитектурные слои. Главные текущие задачи: довести mapping до production-quality, скорость полного сканирования до профессионального уровня и завершить macOS build/signing validation. REAL DATA ONLY. Сначала проверь фактическое состояние GitHub/local, затем работай с измеренным bottleneck.

## 1. Проект

Trader_7_12 Pro — единое macOS read-only приложение для рыночной информации.

Оно:
- анализирует реальные BASE/SPOT инструменты;
- считает D1 quality;
- считает current relative strength против IMOEX2;
- анализирует M5, money flow, liquidity и acceleration;
- формирует Long/Short/Watch/Context только по объективным правилам;
- отдельно показывает Futures OI и futures liquidity;
- НЕ торгует и НЕ выставляет заявки.

Главный принцип:

```text
UP market   → сильные относительно рынка → Long candidates
DOWN market → слабые относительно рынка → Short candidates
NEUTRAL     → строгий directional candidate не создаём
```

```text
RS = PRICE Δ% − IDX Δ%
```

Benchmark = `IMOEX2`, fallback `IRUS2` только при необходимости. Meaningful RS = `0.10 pp`.

## 2. BASE universe

```text
ALL MOEX TQBR STOCKS
GOLD
OIL
GAS
USDRUB
```

Только реальные BCS BASE/SPOT. Нельзя использовать futures как SPOT substitute, synthetic quote, fake classCode/ticker/liquidity или нули вместо missing data.

## 3. Liquidity / M5

```text
MIN_MONEY_PER_MINUTE        = 8000 ₽/min
MIN_RECENT_MONEY_PER_MINUTE = 5000 ₽/min
```

Оба hard gates обязательны для strict candidate.

Acceleration:

```text
recent complete 15m pace / previous complete 15m pace - 1
```

Нужны 3 M5 candles в каждом полном окне и positive previous flow.

Production M5 coverage minimum = 80%; ниже → `INSUFFICIENT_COVERAGE`.

## 4. D1

`DailyTrendProfileService` deterministic/no network.

STRONG = зелёные candles + строго растущие High + Low + положительный D1 RS относительно IMOEX2 каждый сопоставленный день. WEAK — зеркально.

D1 — quality/context, не замена current RS.

## 5. Futures OI

Source = MOEX RFUD marketdata.

Primary OI = real SECID marketdata. FUTOI = supplemental.

Front:

```text
ACTIVE → NON-EXPIRED → OI > 0 → NEAREST EXPIRY → FRONT
```

Liquidity = only RFUD `VALTODAY`.

Never use PRICE × VOLUME, synthetic VALUE/turnover or manual promotion of roots.

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

Examples include `SIU6 → USDRUB`, `CRU6 → CNYRUB`, `MXU6 → IMOEX`, `GDU6 → GLDRUB_TOM`, `RIU6 → RTS`, `SRU6 → SBER/TQBR`, `GZU6 → GAZP/SMAL`, `EUU6 → EUR_RUB__TOM/CETS`.

MIX and IMOEXF remain separate futures products even when economic underlying is IMOEX.

## 6. Mapping — CURRENT P0

Mapping is improved but not production-complete.

Latest important diagnostic:

```text
underlying_requested = 195
underlying_class_codes = 48
underlying_class_code_missing = 147
underlying_metadata_lookup_batches = 2
underlying_metadata_lookup_records = 148
underlying_exact_matches = 48
underlying_semantic_matches = 0
```

The 147 missing entries must be classified:

```text
A. supported BASE requiring BASE Δ%
B. futures-only outside BASE
C. genuinely unresolved BCS mapping
```

BCS live metadata is source of truth. Catalog is preferred lookup only. No synthetic fallback.

## 7. Performance — CURRENT P1

Already implemented:
- process-wide BCS API singleton;
- candle cache/retry/bounded concurrency;
- shared BCS metadata cache;
- SPOT universe cache reuse;
- partial futures/index mapping cache reuse;
- D1 parallelization with `D1_MAX_WORKERS = 6`;
- `timings_seconds` diagnostics.

Current candle concurrency = 4. Do not blindly increase it.

Exact workflow:

```text
1. run one real scan;
2. copy DIAGNOSTICS;
3. inspect timings_seconds;
4. identify dominant phase;
5. fix only measured bottleneck;
6. pytest;
7. build;
8. measure again.
```

Likely bottlenecks: metadata/universe, M5 history/session requests, or duplicated BCS metadata calls. Do not weaken trading criteria for speed.

## 8. UI / sound

One application only:

```text
RADAR
FUTURES OI
DIAGNOSTICS
SETTINGS
```

Real Qt tables, sorting, copy, scan visual overlay, persistent sound settings.

Sound status tested 13.09.2026:
- final completion melody = **WORKS**;
- final melody plays after complete RADAR + Futures OI workflow;
- start melody = **NOT HEARD / NOT CONFIRMED**.

Latest sound commit: `89d63cd`.

## 9. macOS build/signing — CURRENT BLOCKER

The previous build reached PyInstaller BUNDLE but failed signing with:

```text
resource fork, Finder information, or similar detritus not allowed
```

Diagnostics proved:

```text
source Python.framework → clean
source PySide6 → clean
build/ → clean
dist/ → contaminated
```

Generated `dist` contained `com.apple.FinderInfo` and `com.apple.fileprovider.fpfs#P` on nested Python/PySide6 frameworks. No `._*` files and no `com.apple.ResourceFork` were found.

Therefore post-build `xattr -cr` was too late: PyInstaller itself attempts BUNDLE signing before the script's cleanup stage.

### Implemented fix

Commit:

```text
f2e0aff5bf5034aa483cb81b3834640735feb382
```

`build_mac_app.sh` was changed to stage PyInstaller output outside the affected project/File Provider metadata tree, then perform controlled final signing/verification before putting the production `.app` into `dist`.

**This fix is committed but NOT YET LOCALLY VERIFIED.** Do not call the build green until the real local run ends with:

```text
=== APP BUILD OK ===
Code signing: ad-hoc verified
```

## 10. Tests

Latest confirmed regression:

```text
121 passed in 1.21s
```

Build script test stage also reported:

```text
121 passed in 1.34s
```

## 11. Next exact command

On the user's iMac:

```bash
cd ~/Documents/Trader_7_12 && \
git pull --ff-only origin main && \
./scripts/build_mac_app.sh
```

Do not run more signing diagnostics before this build. The root cause is already established and the staging fix is committed.

After successful build, launch:

```bash
cd ~/Documents/Trader_7_12 && \
pkill -f "Trader_7_12 Pro" 2>/dev/null || true && \
open "dist/Trader_7_12 Pro.app"
```

Then verify:
1. app opens;
2. single-window UI intact;
3. RADAR scan works;
4. Futures OI works;
5. final sound works;
6. start sound remains the next audio/UI item if still absent;
7. diagnostics show real timings.

## 12. Important files

```text
Program/api/bcs_api.py
Program/api/bcs_underlying_catalog.py
Program/services/bcs_metadata_cache_service.py
Program/services/spot_universe_service.py
Program/services/market_attention_scanner_service.py
Program/services/history_candle_service.py
Program/services/daily_trend_profile_service.py
Program/services/futures_oi_marketdata_scanner_service.py
Program/services/market_session_service.py
Program/ui.py
Program/oi_watchlist_ui.py
Program/professional_window.py
Program/main.py
scripts/build_mac_app.sh
scripts/Trader_7_12_Pro.spec
Docs/PROJECT_PASSPORT.md
Docs/NEW_CHAT_STATE.md
```

## 13. Non-negotiable rules

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

## 14. Definition of professional completion

- supported BASE mapping materially complete and verified against real BCS metadata;
- unresolved mappings honestly classified;
- no synthetic fallback;
- full scan speed measured and predictable;
- repeated metadata requests deduplicated;
- M5/D1 access cached safely;
- coverage/diagnostics truthful;
- Futures OI uses real RFUD/OI/VALTODAY;
- Radar uses true RS vs market;
- regression suite green;
- macOS build green and signature verified;
- one coherent professional application.
