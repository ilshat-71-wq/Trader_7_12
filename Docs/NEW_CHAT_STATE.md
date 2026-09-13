# TRADER_7_12 PRO — NEW CHAT STATE / HANDOFF

**Состояние на:** 13.09.2026  
**Repo:** `ilshat-71-wq/Trader_7_12`  
**Branch:** `main`  
**Latest commit after passport update:** `3c72f23e2f8dd740324ceaf1556b8feb10141b`  
**Previous functional commit:** `89d63cd807afcbb28d0ca35d9e5f2022ce498532`

## 0. Готовая инструкция для нового чата

В новом чате пользователь может написать:

> Продолжаем существующий проект TRADER_7_12. Это НЕ новый проект. Прочитай `Docs/PROJECT_PASSPORT.md` и `Docs/NEW_CHAT_STATE.md` в GitHub и продолжай строго с текущего состояния. Я — автор идеи и требований, ты — архитектор и технический руководитель. Не создавай новые приложения, мини-сканеры или лишние архитектурные слои. Главные текущие задачи: довести mapping до production-quality и довести скорость полного сканирования до нормального профессионального уровня. REAL DATA ONLY. Сначала проверь текущее состояние GitHub/local, затем работай с фактическим bottleneck.

## 1. Что это за проект

Trader_7_12 Pro — единое macOS read-only приложение для рыночной информации.

Оно:
- анализирует реальные BASE/SPOT инструменты;
- считает D1 quality;
- считает current relative strength против IMOEX2;
- анализирует M5, money flow, liquidity и acceleration;
- формирует Long/Short/Watch/Context только по объективным правилам;
- отдельно показывает Futures OI и futures liquidity;
- НЕ торгует и НЕ выставляет заявки.

## 2. Главный принцип

Не угадывать абсолютное направление отдельной бумаги.

```text
UP market   → сильные относительно рынка → Long candidates
DOWN market → слабые относительно рынка → Short candidates
NEUTRAL     → строгий directional candidate не создаём
```

```text
RS = PRICE Δ% − IDX Δ%
```

Benchmark: `IMOEX2`; `IRUS2` — fallback только при невозможности использовать IMOEX2.

Meaningful RS = `0.10 pp`.

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
- создавать synthetic quote;
- ставить 0 при отсутствии данных;
- считать отсутствие данных отсутствием движения.

GOLD → `GLDRUB_TOM` при наличии real BCS SPOT.  
USDRUB → real SPOT.  
OIL/GAS → только real BASE/SPOT; иначе UNAVAILABLE.

## 4. Liquidity

```text
MIN_MONEY_PER_MINUTE        = 8000 ₽/min
MIN_RECENT_MONEY_PER_MINUTE = 5000 ₽/min
```

Оба hard gates обязательны для strict candidate.

Acceleration:

```text
recent complete 15m pace / previous complete 15m pace - 1
```

Нужны 3 M5 candles + 3 M5 candles и positive previous flow.

## 5. D1

`DailyTrendProfileService` deterministic/no network.

STRONG = green candles + strictly rising High + strictly rising Low + positive D1 RS every matched day.  
WEAK = зеркально.

D1 — quality/context, не замена current RS.

## 6. M5 / coverage

Production coverage minimum = 80%.

<80% → `INSUFFICIENT_COVERAGE`.

Missing data visible in diagnostics.

## 7. Futures OI

Source = MOEX RFUD marketdata.

Primary OI = real SECID marketdata.  
FUTOI = supplemental.

Front:

```text
ACTIVE → NON-EXPIRED → OI > 0 → NEAREST EXPIRY → FRONT
```

Liquidity = only RFUD `VALTODAY`.

Never use:
- PRICE × VOLUME;
- undefined VALUE;
- synthetic turnover;
- manual promotion of expected roots.

## 8. Canonical futures underlying mappings

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

MIX and IMOEXF are separate futures products even when economic underlying is IMOEX.

## 9. Mapping problem — CURRENT PRIORITY #1

Mapping has improved substantially but is not finished.

Historical diagnostics showed:

```text
earlier: 41.21% mapping coverage
later:   24.12% mapping coverage
```

Later diagnostic:

```text
underlying_requested = 195
underlying_class_codes = 48
underlying_class_code_missing = 147
underlying_metadata_lookup_batches = 2
underlying_metadata_lookup_records = 148
underlying_exact_matches = 48
underlying_semantic_matches = 0
```

These 147 are NOT automatically 147 broken mappings.

Next action:

```text
A. supported BASE universe needing BASE Δ%
B. futures-only instruments outside BASE universe
C. genuinely unresolved BCS mappings
```

Then repair C and verify A using real BCS metadata.

BCS preferred catalog:

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

Catalog is lookup preference only. Live BCS metadata is source of truth.

Real BCS alias example: `EUR_RUB__TOM` may correspond to requested `EURRUB_TOM`; normalize only for matching an actual returned record, never invent it.

## 10. Speed problem — CURRENT PRIORITY #2

User reported scanner is very slow, even slower than before.

Already done:
- process-wide BCS API singleton;
- candle cache/retry/bounded concurrency;
- shared BCS metadata cache;
- SPOT universe uses shared metadata cache;
- partial futures/index mapping cache reuse;
- D1 profiles parallelized with `D1_MAX_WORKERS = 6`;
- `timings_seconds` added to Radar diagnostics.

Current Radar version = `2.5.1`.

Current BCS candle concurrency is bounded at 4, so do NOT blindly raise workers.

Next exact workflow:

```text
1. run one real scan;
2. copy DIAGNOSTICS;
3. inspect timings_seconds;
4. identify dominant phase;
5. fix only measured bottleneck;
6. run pytest;
7. build app;
8. measure full scan again.
```

Potential bottlenecks:

```text
universe / metadata
→ central cache + in-flight dedupe

M5
→ history candle/session cache + request dedupe

D1
→ measure actual post-parallel timing first

BCS metadata
→ eliminate repeated full instrument-page loading
```

Do not weaken market criteria to make scan appear faster.

## 11. Architecture files that matter

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
Docs/PROJECT_PASSPORT.md
```

## 12. Current UI

One application only:

```text
RADAR
FUTURES OI
DIAGNOSTICS
SETTINGS
```

Real Qt tables, sorting, copy, scan visual overlay, persistent sound settings.

## 13. Sound status

User tested latest build:

- final completion melody: **WORKS**;
- final melody plays after complete RADAR + Futures OI workflow;
- start melody: **NOT WORKING / NOT HEARD** according to latest user report.

Latest sound commit:

```text
89d63cd — Fix completion sound to fire after full scan
```

Do not confuse this UI issue with market-data pipeline.

## 14. Tests/build

Last confirmed regression before latest sound work:

```text
111 passed
```

Standard local verification:

```bash
cd ~/Documents/Trader_7_12 && \
git pull --ff-only && \
python3 -m compileall -q Program && \
pytest -q && \
./scripts/build_mac_app.sh
```

Launch:

```bash
cd ~/Documents/Trader_7_12 && \
pkill -f "Trader_7_12 Pro" 2>/dev/null || true && \
open "dist/Trader_7_12 Pro.app"
```

## 15. Important historical commits

```text
5cfa792  Add shared process BCS metadata cache
 d363e02 Use shared BCS metadata cache in SPOT universe
c681166  Improve shared BCS metadata reuse for underlying mapping
2a65b6c  Cache real INDEX metadata for futures underlying mapping
6ab8d45  Speed up Radar D1 stage and expose scan timings
89d63cd  Fix completion sound to fire after full scan
```

## 16. Non-negotiable rules

```text
REAL DATA ONLY
NO SYNTHETIC VALUES
NO FUTURES AS SPOT SUBSTITUTE
NO FAKE CLASS CODES
NO FAKE TICKERS
NO FAKE LIQUIDITY
NO ORDER EXECUTION
NO PORTFOLIO MANAGEMENT
```

Never restart the project. Never split it into separate applications or mini-scanners. Keep one professional application.

## 17. Definition of professional completion

Before calling the project production-ready:

- supported BASE mapping is materially complete and verified against real BCS metadata;
- unresolved mappings are classified honestly;
- no synthetic fallback exists;
- full scan speed is measured and predictable;
- repeated metadata requests are deduplicated;
- M5/D1 candle access is cached safely;
- coverage/diagnostics are truthful;
- Futures OI uses real RFUD/OI/VALTODAY;
- Radar uses true relative strength vs market;
- regression suite green;
- macOS build green;
- UI is one coherent professional application.
