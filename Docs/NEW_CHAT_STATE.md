# TRADER_7_12 PRO — NEW CHAT STATE / HANDOFF

**Состояние:** 13.09.2026

Пользователь ранее подтвердил локальную синхронизацию: `main` = `origin/main` = `d51f9405fc3e36ddb0f42275585a3dcc73882a0e`, working tree чистый.

После этого handoff-файл был обновлён напрямую на GitHub. Перед локальной работой требуется:

```bash
cd ~/Documents/Trader_7_12 && git pull --ff-only origin main
```

## Current priorities

1. P0 — production-quality BCS underlying mapping.
2. P1 — BASE Δ% coverage using real BCS classCode + real M5 data during an open session.
3. Closed-market UI clarity.
4. Final UI polish.

13.09.2026 is Sunday. `MARKET_CLOSED`, zero SPOT universe and absent current LIQ NOW/FLOW are expected. Never synthesize data.

Observed Futures OI: 600 raw, 199 active, 233 analyzed, 233 OI available, 224 liquidity available, top 20 returned; real RFUD `VALTODAY`; money flow `NO_DATA` while closed.

Observed mapping defect: 195 requested, 48 class codes, 147 missing, 48 exact matches, 0 semantic matches, 24.12% coverage. Missing entries must be classified as supported BASE, futures-only outside BASE, or genuinely unresolved BCS mapping.

REAL DATA ONLY. NO SYNTHETIC VALUES. NO FUTURES AS SPOT SUBSTITUTE. NO FAKE CLASS CODES/TICKERS/LIQUIDITY. NO ORDER EXECUTION. NO PORTFOLIO MANAGEMENT. One application only. Work on `main`.
