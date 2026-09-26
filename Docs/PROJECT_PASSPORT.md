# TRADER_7_12 PRO — PROJECT PASSPORT

**Дата актуализации:** 26.09.2026  
**Репозиторий:** `Trader_7_12`  
**Ветка:** `main` — единственная рабочая ветка  
**Статус:** production-oriented read-only market-information scanner  
**Radar pipeline:** 2.5.1  
**Futures OI scanner:** 2.7.20  
**Последний функциональный commit:** `0ad611d789d45246792cf5faebb907ebb9dedd6c`  
**Последний локально подтверждённый regression suite:** `149 passed, 1 warning` (23.09.2026)  
**Последний regression-test commit:** `42c62f446a7d28240c68123aca8fe2f57e575bf0`  
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


## 0.4 New-chat recovery protocol — CANONICAL

**Purpose:** a new ChatGPT chat must recover the project from GitHub and the canonical passport instead of relying on conversational memory.

### Source of truth
1. GitHub repository: `ilshat-71-wq/Trader_7_12`
2. Working branch: `main` — the only working branch.
3. Canonical project passport: `Docs/PROJECT_PASSPORT.md`
4. Current code on `main` is authoritative for implementation details.
5. ChatGPT memory/context is auxiliary only; it must never override GitHub, the passport, tests, or verified live results.

### Mandatory new-chat sequence
When the user says to continue Trader_7_12 in a new chat, first:
1. Read `Docs/PROJECT_PASSPORT.md` from GitHub `main`.
2. Check the latest commit on `main`.
3. Compare the passport checkpoint with the latest commit and current code where the difference matters.
4. Restore the current project state: implemented, verified, known limitations, open investigation, and next step.
5. Do not restart the project, re-ask already documented context, invent missing implementation details, or assume that an old chat state is still current.
6. For any uncertainty, use the sequence: **memory/context → hypothesis → GitHub/code → tests → real check**.
7. Never report an item as verified unless the relevant code/test/live/build evidence exists.

### Mandatory local synchronization after a new-chat recovery
On the user's Mac, the project must be synchronized to the same GitHub `main` before local acceptance:
```bash
cd ~/Documents/Trader_7_12 && \
git fetch origin && \
git switch main && \
git pull --ff-only origin main && \
echo "=== SYNC CHECK ===" && \
git status --short --branch && \
git log -1 --oneline
```
Expected state: `main` tracks `origin/main`, working tree clean, and local HEAD equals the latest GitHub `main` commit.

### Mandatory acceptance sequence
After synchronization, use the project workflow:
```
code/change
→ tests
→ real check
→ commit to main
→ update PROJECT_PASSPORT.md
→ push main
→ local pull
→ build
→ open the single Trader_7_12 Pro.app
→ app check
```

### Passport update rule
After every material project change, update this same canonical passport. Do not create a second project passport, replacement concept document, or parallel status MD.

The checkpoint must record, when applicable:
- current GitHub `main` HEAD;
- application/scanner versions;
- latest confirmed tests;
- latest real/live check;
- latest successful macOS build;
- current architecture and data-source constraints;
- open investigations;
- next concrete step;
- important things that must not be changed.

### Current recovery checkpoint — 26.09.2026
- GitHub `main` latest commit: `0ad611d789d45246792cf5faebb907ebb9dedd6c` — `Fix Final Radar day-change regression setup`.
- Immediately preceding merged checkpoint: `2e4e6d2f2e13f3ce985a45ba95f9efa34d0bab38` — `Fix Morning Radar and Futures confirmation gate`.
- Current targeted regression result after the recent Final Radar work: `23 passed, 1 warning`.
- Last previously confirmed full Program suite: `170 passed, 1 warning` before the latest commits; this is not to be presented as a fresh post-commit full-suite result until rerun.
- Known warning: Python 3.14 / `pytest_asyncio` deprecation concerning `asyncio.get_event_loop_policy`; not a project failure.
- Morning Radar startup persistence fix is on `main`.
- Final Radar missing Futures mapping gate is on `main`: SPOT Final is blocked on `NO_MATCH`.
- Open realtime investigation: verify from live-market evidence whether `FLOW RT` is an independent source or an aggregate derived from BOOK/TAPE. Do not change the implementation until evidence is collected.
- Weekend control run showed insufficient SPOT coverage and zero strict candidates; this is a data/session condition, not a reason to weaken the gates.
- Next live validation: **OI → FLOW → BOOK → TAPE → FLOW RT → Final Radar**, with sequential scans required for Final persistence.

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

The current source checkpoint is ready for local iMac synchronization. A successful build/open on the iMac is the acceptance step; do not claim it is green until the local command actually returns the verification line.

## 18. Tests

Latest confirmed local regression after realtime checkpoint:

```text
149 passed, 1 warning in 2.45s
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

### P0 — iMac application synchronization
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
