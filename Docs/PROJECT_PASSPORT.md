# TRADER_7_12 PRO — PROJECT PASSPORT

**Дата актуализации:** 08.09.2026  
**Репозиторий:** `ilshat-71-wq/Trader_7_12`  
**Ветка:** `main` — единственная рабочая ветка  
**Статус:** production-oriented read-only market-information scanner  
**Версия pipeline:** 2.4.1

## 1. Назначение

Trader_7_12 Pro — **read-only информационный сканер рынка**. Его задача — в течение текущего торгового дня показывать реальные факты о состоянии доступных BASE/SPOT-инструментов: дневную структуру, относительную силу/слабость к IMOEX2, текущую активность и денежный поток, раннее поведение и реакцию на внутридневные экстремумы индекса.

Сканер не выставляет заявки, не управляет позициями, не рассчитывает размер позиции, SL/TP и **не принимает торговое решение за пользователя**.

## 2. Каноническая D1-классификация

### STRONG — сильная дневная структура

На последних **2–3 завершённых D1 свечах** одновременно:

- все свечи зелёные (`Close > Open`);
- High строго растёт от дня к дню;
- Low строго растёт от дня к дню;
- в каждый сопоставленный день актив сильнее IMOEX2: его дневная доходность выше доходности индекса.

Это объективная классификация состояния инструмента. Она не является торговой рекомендацией.

### WEAK — слабая дневная структура

На последних **2–3 завершённых D1 свечах** одновременно:

- все свечи красные (`Close < Open`);
- High строго падает от дня к дню;
- Low строго падает от дня к дню;
- в каждый сопоставленный день актив слабее IMOEX2: его дневная доходность ниже доходности индекса.

Это объективная классификация состояния инструмента. Она не является торговой рекомендацией.

Смешанная структура или непоследовательный дневной RS не квалифицируют инструмент как STRONG/WEAK. Текущий M5 RS — отдельный текущий факт и не заменяет D1-классификацию.

## 3. Канонический universe

```text
ALL MOEX TQBR STOCKS
GOLD
OIL
GAS
USDRUB
```

- GOLD: `GLDRUB_TOM`, если доступен в BCS SPOT metadata.
- USDRUB: реальный spot-инструмент из BCS metadata.
- OIL/GAS: не заменяются фьючерсами; без real base/spot source → `UNAVAILABLE`.
- Futures metadata, expiry, mapping и ranking обрабатываются отдельным futures OI слоем и не заменяют BASE/SPOT analysis.
- На ДСВД stock universe фильтруется по MOEX `WEEKENDSESSION`, если поле доступно; `WEEKENDSESSION=N` исключается.
- Если `WEEKENDSESSION` не отдан BCS, бумага не удаляется молча; фактическая M5-доступность может использоваться как дополнительная проверка.

## 4. Production information pipeline

```text
BASE/SPOT UNIVERSE
→ COMPLETED D1 STRUCTURE
→ DAILY RS VS IMOEX2
→ CURRENT SESSION M5
→ EARLY SESSION BEHAVIOUR
→ PRICE / CHANGE / ₽×V / ₽×V-MIN
→ IMOEX2 MIN/MAX REACTION
→ RECENT 15-MIN FLOW
→ ABSOLUTE LIQUIDITY GATE
→ FLOW ACCELERATION
→ CURRENT INTRADAY RS VS IMOEX2
→ MARKET LEADERS / MARKET LAGGARDS
→ ATTENTION RANKING
```

Результат — информационная картина рынка на текущий момент. Программа не говорит пользователю, что покупать, продавать, лонговать, шортить или когда входить.

## 5. Daily Trend Profile contract

`DailyTrendProfileService` is deterministic and network-free. The caller supplies historical D1 candles.

- Current/incomplete trading day is excluded by trading date.
- Daily candles are aligned to Moscow trading date.
- Asset and benchmark are compared by common date, never merely by array position.
- Minimum D1 history: 2 completed days; target: 3.
- Strong/weak structure requires both rising/falling Highs and Lows plus all-green/all-red candles.
- Daily relative confirmation must be consistent across all selected days.
- The service never creates a directional trading signal from incomplete or mixed data.

## 6. Intraday information

Основной внутридневной timeframe: M5. Recent flow window: 15 minutes.

Для каждой доступной бумаги по возможности показываются:

- текущая цена и изменение;
- сессионный ₽×V;
- сессионный ₽×V/min;
- последние 15 минут ₽×V и ₽×V/min;
- ускорение денежного потока;
- текущий RS против IMOEX2;
- ранняя активность;
- реакция на дневной MIN и MAX IMOEX2;
- текущая позиция относительно рынка.

## 7. Flow acceleration — production contract

Acceleration compares two complete, equal 15-minute M5 windows:

```text
recent 15-min pace / previous 15-min pace - 1
```

Valid only when both windows contain 3 M5 candles and previous flow is positive. Otherwise `money_acceleration = 0.0`.

No artificial acceleration cap is applied. Acceleration has only 10% weight in Attention and cannot alone determine market classification.

Attention score:

```text
45% recent ₽×V/min
25% session ₽×V
20% session ₽×V/min
10% acceleration percentile
```

## 8. Absolute liquidity gate

Percentile ranking is not allowed to manufacture liquidity. An instrument must first demonstrate meaningful absolute current activity; only then may it compete on relative ranking.

Production scanner-operational thresholds:

```text
MIN_MONEY_PER_MINUTE        = 8 000 ₽/min
MIN_RECENT_MONEY_PER_MINUTE = 5 000 ₽/min
```

Both conditions are required.

## 9. Benchmark / Relative Strength

Only the real market benchmark is allowed:

```text
IMOEX2 → IRUS2 fallback only if IMOEX2 unavailable/unfit
```

Current-session RS:

```text
RS = asset_current_session_return - benchmark_current_session_return
```

Daily RS:

```text
daily RS = asset_D1_return - IMOEX2_D1_return
```

Meaningful current RS floor:

```text
MIN_MEANINGFUL_RS_PP = 0.10 percentage points
```

## 10. Market leader / laggard selection

The scanner may select at most the strongest current market leader and weakest current market laggard from instruments that satisfy all required objective information gates.

This is an informational classification only. The application does not make a trade decision.

When strict qualification is unavailable because D1 history or M5 coverage is insufficient, the radar does **not** erase the available market information. It may show up to the configured radar capacity as `ATTENTION_WATCH` / `WATCH_ONLY`, provided absolute liquidity and meaningful current RS are present. These rows are explicitly not strict qualifications and never become BUY/SELL or execution signals.

## 11. Output / UI contract

Основной экран ориентирован на фактическую картину рынка:

```text
ЛИДЕРЫ
АУТСАЙДЕРЫ
ТОП ПО ТЕКУЩЕМУ ИНТЕРЕСУ
FUTURES OI — ВСЕ ДОСТУПНЫЕ ROOTS
```

Для futures/OI в отдельной видимой панели показываются:

```text
FUTURES ROOT / CONTRACT
UNDERLYING / BASE ASSET
FUTURES PRICE CHANGE
UNDERLYING PRICE CHANGE
OPEN INTEREST
ΔOI %
OI Z-SCORE
OI REGIME
DIRECTION ALIGNMENT
CURVE ROLE
OI STRENGTH
```

## 12. Calendar / DSWD

Weekend is not automatically CLOSED.

```text
ordinary:
  MORNING  07:00–10:00 MSK
  MAIN     10:00–19:00 MSK
  EVENING  19:00–23:50 MSK

DSWD:
  09:50–19:00 MSK
```

**05.09.2026 is a real DSWD trading day, 09:50–19:00 MSK.**

## 13. Coverage gate

Minimum production M5 coverage: **80%**.

Below 80%:

```text
status = INSUFFICIENT_COVERAGE
```

The 80% threshold remains a diagnostic completeness gate. It no longer deletes all visible candidates: strict `QUALIFIED` rows remain eligible, while objectively supported but incomplete rows may be shown as `ATTENTION_WATCH / WATCH_ONLY`. Partial scan is never relabeled as a complete market result.

## 14. HTTP resilience

- One process-wide read-only BCS client.
- `MAX_WORKERS = 6`.
- Global request-start throttle: `0.15 s` between requests.
- Reusable `requests.Session` with connection pooling per worker.
- HTTP/SSL failure is not interpreted as no trading.
- 429/SSL degradation must reduce coverage and remain visible in diagnostics.

## 15. Open Interest — futures analytics

OI is a separate, reusable analytics layer for **all supported MOEX futures roots**, not a SI-only rule.

Source:

```text
MOEX ISS → /iss/analyticalproducts/futoi/securities
```

The MOEX derivatives market publishes open interest alongside price, volume and trades; MOEX also exposes underlying information for futures contracts.

The production OI layer calculates:

```text
OI
ΔOI contracts
ΔOI %
OI history
OI-change Z-score
Price + OI regime
Volume confirmation
```

Canonical regimes:

```text
PRICE ↑ + OI ↑ → NEW_POSITION_BUILDING_UP
PRICE ↑ + OI ↓ → SHORT_COVERING
PRICE ↓ + OI ↑ → NEW_POSITION_BUILDING_DOWN
PRICE ↓ + OI ↓ → LONG_LIQUIDATION
```

OI itself never determines direction. Price is the directional axis; volume is the activity confirmation; OI explains whether open exposure is building or unwinding.

### OI Z-score

Z-score is calculated from historical daily percentage changes in OI, using the latest 20 observations when sufficient history exists:

```text
|Z| < 1   NORMAL
1–2      ELEVATED
2–3      STRONG
>3       ANOMALOUS
```

### 15.1 Futures → underlying mapping — generic

The mapping is **not hardcoded for SI**. Runtime BCS futures metadata is the source of truth for each futures root.

BCS `/instruments/by-type` can return the futures universe without `classCode` and expiry fields. The production scanner therefore enriches each futures ticker through BCS `/instruments/by-tickers` before requesting quotes. `classCode` is never guessed or hardcoded.

```text
FUTURES ROOT / CONTRACT
        ↓
BCS /by-tickers metadata enrichment
        ↓
underlyingAsset / underlyingTicker / classCode / expiry
        ↓
FUTURES QUOTE + BASE/UNDERLYING QUOTE
        ↓
MOEX FUTOI by futures root
```

For example, SI is represented as:

```text
Si-9.26
futures_root = SI
underlying_asset = USDRUB
```

The source code may be `USDRUB_TOM`; the UI normalizes this to the display name `USDRUB` while retaining the source code internally.

The same mechanism is used for every futures root returned by BCS metadata: currency, index, commodity and single-stock futures. There is no SI-only branch in the analytics logic.

The scanner keeps **futures price/change** and **underlying price/change** as separate facts. They are not substituted for one another. A `DIVERGENCE` state is exposed when their directions disagree.

### 15.2 Curve / rollover handling

For each futures root the scanner keeps the nearest non-expired contract as `FRONT` and exposes curve rank/role metadata for `NEXT` and deferred maturities. MOEX FUTOI is treated as root-level OI; the front contract is therefore not allowed to masquerade as the entire root's OI during rollover.

This is important for SI and every other futures curve: falling OI in an expiring front contract is not automatically interpreted as market-wide short covering.

### 15.3 Visible application output

The application contains a dedicated read-only `FUTURES OI` panel. For every analyzed futures root it shows:

```text
ROOT / CONTRACT
BASE ASSET
FUT Δ%
BASE Δ%
OI
ΔOI%
Z
REGIME
ALIGNMENT
CURVE ROLE
OI STRENGTH
```

The panel is updated asynchronously after the main SPOT market scan so the GUI remains responsive. Failure to obtain futures/OI data is shown explicitly and is never converted into a false `0` or `CLOSED` state.

### 15.4 Runtime diagnostics

The futures scanner exposes counts for:

```text
raw_contracts
metadata_lookup_batches
metadata_lookup_ok
metadata_lookup_records
option_filtered
expired_filtered
expiry_available
class_code_available
active_contracts
active_roots
quote_instruments
quote_records
analyzed
skipped
```

This makes an upstream metadata/API failure distinguishable from an actual absence of futures activity.

### 15.5 Information boundary

OI is informational/confirming context. It does not create BUY/SELL, LONG/SHORT, entry, position-sizing or execution decisions.

## 16. Safety boundary

The application is strictly read-only:

```text
NO ORDERS
NO POSITION SIZING
NO SL/TP
NO TRADE EXECUTION
NO AUTOMATIC ENTRY DECISION
NO TRADE RECOMMENDATION
```

The application reports facts and market classifications only. Final decisions remain completely outside the application.
