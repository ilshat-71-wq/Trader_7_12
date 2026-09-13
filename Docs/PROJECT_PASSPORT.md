# TRADER_7_12 PRO — PROJECT PASSPORT

**Дата актуализации:** 13.09.2026  
**Репозиторий:** `Trader_7_12`  
**Ветка:** `main` — единственная рабочая ветка  
**Статус:** production-oriented read-only market-information scanner  
**Radar pipeline:** 2.5.1  
**Futures OI scanner:** 2.7.14  
**Последний подтверждённый commit:** `89d63cd807afcbb28d0ca35d9e5f2022ce498532`

## 1. Назначение

Trader_7_12 Pro — единое read-only приложение для объективного мониторинга текущего рынка. Оно анализирует реальные BASE/SPOT-инструменты, D1/M5, относительную силу к рынку, ликвидность, денежный поток, acceleration и отдельно показывает Futures OI-контекст.

Программа не выставляет заявки, не управляет позициями, не рассчитывает размер позиции, SL/TP и не исполняет сделки.

## 2. Главный принцип

Ключевая идея — **Relative Strength vs Market**, а не угадывание абсолютного направления цены.

```text
РЫНОК РАСТЁТ → ищем сильные относительно рынка → LONG candidates
РЫНОК ПАДАЕТ → ищем слабые относительно рынка → SHORT candidates
NEUTRAL → не создаём искусственный Long/Short
```

Красная цена сама по себе не означает Short, зелёная цена сама по себе не означает Long.

## 3. Канонический BASE universe

```text
ALL MOEX TQBR STOCKS
GOLD
OIL
GAS
USDRUB
```

Правила:
- GOLD → реальный BCS SPOT/base `GLDRUB_TOM`, если доступен.
- USDRUB → реальный BCS SPOT.
- OIL/GAS → только реальный BASE/SPOT source; futures нельзя использовать как замену.
- Отсутствие реального источника → `UNAVAILABLE`/diagnostic, никогда synthetic value.
- Futures metadata/mapping/OI — downstream context и не заменяют BASE/SPOT.

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

Benchmark: `IMOEX2`, fallback `IRUS2` только если IMOEX2 unavailable/unfit.

Current RS:

```text
RS = PRICE Δ% − IDX Δ%
```

Meaningful threshold: `0.10 pp`.

Market regime:

```text
benchmark >= +0.10 pp → UP
benchmark <= -0.10 pp → DOWN
otherwise → NEUTRAL
```

## 5. D1 quality

`DailyTrendProfileService` детерминированный и без сети.

STRONG:
- все выбранные D1 свечи зелёные;
- High строго растёт;
- Low строго растёт;
- актив сильнее IMOEX2 в каждом сопоставленном дне.

WEAK — зеркально.

Смешанная структура не получает STRONG/WEAK.

D1 — quality/context gate; он не должен подменять current relative-strength logic.

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

Production M5 coverage minimum: **80%**.

Ниже 80% → `INSUFFICIENT_COVERAGE`.

Missing real data всегда остаётся missing/UNAVAILABLE/diagnostic. Нельзя превращать отсутствие данных в «нет движения», нули или synthetic values.

## 8. UI

Единое macOS-приложение `Trader_7_12 Pro.app`.

Вкладки:

```text
RADAR
FUTURES OI
DIAGNOSTICS
SETTINGS
```

Основная Radar-таблица:

```text
# | Ticker | Role | D1 | D1-RS | IDX Δ% | Price Δ% | RS | ₽/min | DAY ₽ | 15m | Accel | Score
```

Это реальная Qt table. UI не изменяет расчёты, qualification, ranking или порядок результатов.

## 9. Futures OI

Источник:

```text
MOEX RFUD marketdata / securities
```

Основной OI — реальный MOEX RFUD marketdata по реальному SECID. FUTOI — supplemental.

Family строится из SECID: например `ALU6 → AL`, `SiM7 → SI`.

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

Futures liquidity — только `VALTODAY` из RFUD. Никаких `PRICE × VOLUME`, synthetic VALUE или ручного проталкивания тикеров в TOP20.

## 10. Futures BASE mapping

Экономическое underlying и конкретный futures contract — разные сущности.

Ключевые canonical mappings:

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

Примеры:

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

MIX и IMOEXF не объединяются в один futures product: они могут иметь один economic underlying `IMOEX`, но остаются разными контрактами.

BCS mapping policy:
1. canonicalize futures family;
2. determine economic underlying;
3. preferred catalog lookup;
4. real BCS `get_instruments_by_tickers()`;
5. accept only real BCS instrument records;
6. use real ticker + real classCode;
7. normalize ticker aliases such as `EUR_RUB__TOM` ↔ `EURRUB_TOM` only for matching real records;
8. quote only accepted real ticker/classCode;
9. no synthetic instrument/quote/class/price.

Preferred catalog pairs include:

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

Catalog — preferred lookup only; real BCS metadata remains source of truth.

## 11. Mapping status / known problem

Mapping has already been materially improved, but **mapping and speed are not yet declared professional-complete**.

Known diagnostics seen during development:

```text
earlier:
  fallback_matches = 17
  underlying_semantic_matches = 128
  underlying_class_codes = 82
  mapping coverage ≈ 41.21%

later diagnostic:
  underlying_requested = 195
  underlying_class_codes = 48
  underlying_class_code_missing = 147
  underlying_metadata_lookup_batches = 2
  underlying_metadata_lookup_records = 148
  underlying_exact_matches = 48
  underlying_semantic_matches = 0
  mapping coverage ≈ 24.12%
```

**Do not interpret the 147 missing entries as 147 broken BASE mappings.** Их нужно разделить на:

1. futures outside the canonical BASE universe;
2. supported BASE instruments requiring BASE Δ%;
3. genuinely unresolved BCS mappings.

Следующий mapping milestone — получить честную классификацию всех unresolved entries и довести supported BASE mapping coverage до production-quality без synthetic fallback.

## 12. BCS/API architecture

- process-wide singleton read-only `BCSAPI`;
- candle cache TTL около 30s;
- candle timeout/retry bounded;
- global candle concurrency bounded (`4` in current BCSAPI);
- shared process-wide metadata cache уже добавлен;
- SPOT universe уже использует shared metadata cache;
- futures underlying/index mapping частично использует shared metadata reuse/cache.

Основная оставшаяся архитектурная задача по performance — убрать дублирование metadata lookups между BCSAPI, SPOT, Market Attention и Futures OI и сделать единую cache/in-flight deduplication точку, не увеличивая без измерений сетевую конкуренцию.

## 13. Current performance state

Последняя оптимизация:

```text
6ab8d45 — Radar D1 stage parallelized + timings
```

`MarketAttentionScannerService.VERSION = 2.5.1`.

D1 profiles теперь получают bounded parallelism `D1_MAX_WORKERS = 6`.

Добавлены timings:

```text
universe
benchmark
benchmark_d1
m5
d1
calculation
total
```

Они сохраняются в `_last_scan_diagnostics` как `timings_seconds`.

**Важно:** глобальная BCS candle concurrency сейчас ограничена 4, поэтому дальнейшее простое увеличение worker count без измерений не является решением.

Следующий performance workflow:

```text
1. получить реальный timings_seconds одного полного scan;
2. определить dominant phase;
3. если universe/metadata → централизовать cache + in-flight dedupe;
4. если M5 → history/session candle cache + request dedupe;
5. если D1 → проверить actual latency после parallelization;
6. не менять trading criteria ради скорости;
7. после каждой оптимизации regression + measured scan time.
```

Цель — профессионально предсказуемое время полного сканирования без потери real-data integrity.

## 14. HTTP/resilience

- HTTP/SSL failure не равен отсутствию торгов;
- bounded retry;
- coverage/diagnostics отражают деградацию;
- Futures OI использует общий `RequestHelper` с TLS/retry;
- не создавать ad-hoc urllib client для OI.

## 15. Calendar

```text
MORNING  07:00–10:00 MSK
MAIN     10:00–19:00 MSK
EVENING  19:00–23:50 MSK
DSWD     09:50–19:00 MSK
```

Weekend не должен автоматически подменяться пятничными данными.

На Sunday 13.09.2026 состояние `MARKET_CLOSED`, current BASE Δ% = unavailable без текущего session window — корректно. Futures нельзя использовать для заполнения SPOT.

## 16. Sound / scan workflow

Sound settings находятся в SETTINGS.

Проверено пользователем 13.09.2026:

- во время сканирования/процесса мелодия ожидаемо работает;
- **финальная мелодия теперь играет после полного RADAR + FUTURES OI workflow**;
- пользователь подтвердил: финальная мелодия сыграла;
- **стартовая мелодия пока не подтверждена: пользователь сообщил, что в начале она не играет.** Это отдельная UI/audio проблема и не относится к market calculations.

Последний sound commit:

```text
89d63cd — Fix completion sound to fire after full scan
```

## 17. Build / tests

Build script:

```text
scripts/build_mac_app.sh
```

Application:

```text
dist/Trader_7_12 Pro.app
```

Последний подтверждённый regression result перед последними UI sound changes:

```text
111 passed
```

Перед каждым новым build обязательно:

```bash
python3 -m compileall -q Program
pytest -q
./scripts/build_mac_app.sh
```

## 18. Read-only boundary

```text
NO ORDER EXECUTION
NO BUY/SELL COMMAND
NO POSITION SIZE
NO SL/TP EXECUTION
NO PORTFOLIO MANAGEMENT
```

## 19. Current priorities — STRICT ORDER

### P0 — Mapping correctness
- fully classify unresolved underlying mappings;
- distinguish BASE-required mappings from futures-only mappings;
- verify real BCS ticker/classCode pairs against live metadata;
- improve supported BASE mapping coverage;
- preserve `UNAVAILABLE` when real source is absent;
- add/expand regression tests for every repaired mapping family.

### P1 — Scan speed
- use `timings_seconds` to identify bottleneck;
- centralize BCS metadata cache and in-flight request deduplication;
- avoid repeated full instrument metadata downloads;
- add history candle/session cache where safe;
- keep bounded concurrency and BCS rate/network safety;
- measure before/after each optimization.

### P2 — Diagnostics / acceptance
- make mapping coverage diagnostics explicit and honest;
- expose timing phases clearly in DIAGNOSTICS;
- verify `BASE Δ%`, quote records, class codes and missing reasons;
- ensure low coverage does not hide the market.

### P3 — Audio polish
- fix reliable scan-start cue;
- keep completion cue after full workflow;
- do not touch market logic for audio/UI work.

## 20. Architectural rule for the next chat

**Do not restart the project. Do not create multiple applications. Do not create mini-scanners or redundant architectural layers.**

Continue from the current `main` state. First inspect GitHub/local status and current diagnostics, then fix the highest-priority real bottleneck. Every change must preserve REAL DATA ONLY and the existing trading logic contract.
