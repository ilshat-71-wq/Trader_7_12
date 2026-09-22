# Trader_7_12 Pro — NEW CHAT STATE
## Checkpoint: 22.09.2026

### 1. Current project state
- Repository: `ilshat-71-wq/Trader_7_12`
- Branch: `main`
- Current remote HEAD: `4a1efa6 Fix shared metadata cache import`
- App: `Trader_7_12 Pro.app`
- Bundle version: `2.4.3`
- Architecture: desktop client + separate Cloud Market Data Engine
- Current state is a stable checkpoint. Do not restart or redesign the project.

### 2. Verified tests
Command:
```bash
cd ~/Documents/Trader_7_12 && python3 -m pytest -q Program
```
Result:
- 139 passed
- 1 warning
- warning is Python 3.14 / pytest_asyncio deprecation concerning `asyncio.get_event_loop_policy`
- no test failures

### 3. Cloud Market Data Engine
Launch:
```bash
cd ~/Documents/Trader_7_12 && python3 -m uvicorn Cloud.app:app --host 0.0.0.0 --port 8080
```

Endpoints:
- GET `/health`
- GET `/v1/status`
- GET `/v1/snapshot`
- POST `/v1/scan`
- WS `/v1/stream`

Core architecture:
```
MOEX RFUD
   ↓
D−3 rollover
   ↓
LOCKED TRADING UNIVERSE
   ↓
BCS mapping
   ↓
Futures OI
   ↓
Turnover / Money Flow
   ↓
ONE cached versioned snapshot
   ↓
HTTP API / WebSocket
   ↓
many desktop clients
```

Rules:
- real BCS data only
- no synthetic price × volume
- no participant-identity claims
- locked universe is the admission boundary
- downstream services must not re-expand it
- one scan at a time
- last good snapshot survives refresh failures
- multiple clients must consume the same snapshot rather than trigger separate BCS scans

### 4. Current trading universe
Allowed dated Russian single-stock futures plus:
- USD/RUB
- EUR/RUB
- CNY/RUB
- Brent
- Light Sweet Crude Oil / CL
- Natural Gas
- Gold

Forbidden:
- perpetual / auto-roll futures
- crypto futures
- foreign stock / ETF / FX futures
- index futures
- interest-rate futures
- unapproved commodities/new products

Explicitly forbidden perpetuals:
- `USDRUBF`
- `EURRUBF`
- `CNYRUBF`
- `GAZPF`
- `SBERF`

D−3 rollover:
- source: MOEX RFUD / LASTDELDATE
- if days_to_expiry <= 3: exclude current contract and select next dated contract
- if no next dated contract: skip family
- never use an expiring fallback

Current active examples:
`EUZ6`, `SIZ6`, `BRV6`, `CRZ6`, `ONZ6`, `NGU6`, `GDZ6`, `GLZ6`.

### 5. BCS mapping facts already verified
- `NGU6 / NG-9.26` → base `FEG / NGas1026`
- `NGZ6 / NG-12.26` → same base `FEG / NGas1026`
- `SIZ6` → base market data is `USD000SMALL` on `CETS_FX`
- `USDRUBF` may expose `USD000SMALL` as a base reference, but `USDRUBF` itself is perpetual and must not be used as market-data source
- EUR/RUB mapping is `EUR_RUB__TOM / CETS`; live M5 returned no bars on the tested 2026-09-21 session, so missing EUZ6 Base Δ is treated as genuine BCS data availability, not filled synthetically

### 6. Performance checkpoint
#### Cold scan
- RADAR: 95.855 s
- FUTURES_OI: 9.707 s
- MONEY_FLOW: 9.132 s
- SNAPSHOT: 0.002 s
- TOTAL: 114.696 s

Cold radar:
- UNIVERSE: 37.170 s
- BENCHMARK: 0.470 s
- M5: 29.588 s
- D1: 28.501 s
- CALCULATION: 0.016 s

#### Warm scan, same Cloud process
- RADAR: 59.572 s
- FUTURES_OI: 1.163 s
- MONEY_FLOW: 3.096 s
- SNAPSHOT: 0.003 s
- TOTAL: 63.834 s

Warm radar:
- UNIVERSE: 0.019 s
- BENCHMARK: 0.647 s
- BENCHMARK_D1: 0.062 s
- M5: 30.241 s
- D1: 28.527 s
- CALCULATION: 0.016 s

Conclusion:
- shared metadata cache optimization works
- warm Cloud cycle is back around the established ~63 s level
- M5 and D1 are stable and should NOT be changed without evidence
- Futures OI is already fast
- Money Flow is acceptable
- do not tune candle concurrency/throttle merely for theoretical gains

### 7. Metadata cache
Shared `BCSMetadataCacheService`:
- TTL: 300 s
- full catalog cache by instrument type
- per-batch ticker cache
- in-flight deduplication
- cached catalog reuse for ticker lookups

Important commits:
- `617c97e` Reuse cached BCS catalog for ticker lookups
- `6426e09` Reuse shared BCS catalog for ticker lookups
- `d707f1d` Test shared BCS catalog ticker reuse
- `4a1efa6` Fix shared metadata cache import

The local fix `7a6cea9` was skipped as already applied during rebase. Local main and origin/main are aligned.

### 8. Candle subsystem — DO NOT TOUCH NOW
Current:
- cache TTL 30 s
- timeout 8 s
- max concurrency 6
- global request interval 0.11 s
- retry configuration already validated
- M5 requests are expanded to the Moscow session 07:00–23:59 MSK and then sliced
- latest diagnostics: all candle HTTP requests OK, zero errors

Do not remove session expansion.
Do not blindly increase concurrency.
Do not change timeout/throttle/retry based on the earlier isolated IMOEX2 error.

### 9. Diagnostics
Candle diagnostic commit:
`9b6cbb2c8c1560cf218b9383306dba511af4e191`
- HTTP status counts
- exception counts
- first/last error
- ticker/classCode/status/type/message

Latest full scan:
- M5: 500 requests, 268 cache misses, 500 HTTP OK, 0 errors
- D1: 500 requests, 500 HTTP OK, 0 errors

### 10. Futures OI
Service:
`Program/services/futures_oi_marketdata_scanner_service.py`

MOEX RFUD source and D−3 expiry logic are established.
Latest warm timing: 1.163 s.

Money Flow order-book 404s for several futures are known BCS availability limitations and are not treated as a core scan failure.

### 11. BCS authentication
Do not expose the token.
Cloud README uses:
`BCS_REFRESH_TOKEN`

Token can be obtained from the existing local configuration:
`~/.config/Trader_7_12/bcs_refresh_token`

Verified previously:
- `BCS_REFRESH_TOKEN` resolves successfully
- token length was 856 characters
- never print or commit the token

### 12. App status

**Single-app decision (22.09.2026):** exactly one macOS desktop application exists: `Trader_7_12 Pro.app`. Radar, Futures OI, Diagnostics and Settings are functions of this one client. Cloud Market Data Engine is backend infrastructure, not another desktop application.
Known previous successful build:
- `dist/Trader_7_12 Pro.app`
- installed copy: `~/Applications/Trader_7_12 Pro.app`
- Bundle version 2.4.3
- turquoise-gold watch dial icon
- PyInstaller onedir + macOS .app
- ad-hoc signing

The single application UI has NOT been remotely inspected in this checkpoint because this ChatGPT session does not have a terminal/GUI-control channel into the user's Mac. Do not claim that the app was opened or visually inspected. The next local step is to build/open the current app and inspect the actual UI.

### 13. Immediate next step

Synchronize the iMac with current `main` and build/open the single application.
Do not restart the project.

First, on the user's Mac:
```bash
cd ~/Documents/Trader_7_12 && \
git pull --ff-only origin main && \
./scripts/build_mac_app.sh && \
open "dist/Trader_7_12 Pro.app"
```

Then inspect:
1. main dashboard
2. SPOT panel
3. Futures OI panel
4. all buttons and controls
5. data refresh/status behavior
6. Cloud connection/status presentation
7. whether the UI clearly distinguishes data, signal, and action

Only after visual inspection decide whether UI polishing is needed.

### 14. Next engineering stage after UI inspection
Cloud API / WebSocket / multi-client validation:
- /health
- /v1/status
- /v1/snapshot
- /v1/stream
- snapshot version increments
- last-good snapshot after failed refresh
- POST /v1/scan while another scan is running
- several WebSocket clients receiving the same snapshot
- verify clients do not create additional BCS scans

### 15. Working rule for the next chat
Start from this file and the current remote HEAD.
Do not:
- restart the project
- replace the architecture
- invent synthetic market data
- reintroduce perpetual futures
- change stable candle settings without measured evidence
- rebuild Cloud architecture unnecessarily

The project is at the transition point from data-engine stability to client/API validation and UI inspection.
