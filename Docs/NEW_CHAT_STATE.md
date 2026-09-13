# TRADER_7_12 PRO — NEW CHAT STATE / HANDOFF

**Состояние:** 13.09.2026

## Verified state before handoff edits

Local `main`, `origin/main`, and the running application were verified by the user at `d51f9405fc3e36ddb0f42275585a3dcc73882a0e`; working tree was clean.

This document was then updated directly on GitHub `main`. Therefore the user's local checkout must be fast-forwarded before any further local work:

```bash
cd ~/Documents/Trader_7_12 && git pull --ff-only origin main
```

## Current technical priorities

1. P0: production-quality BCS underlying mapping.
2. P1: BASE Δ% coverage through real BCS classCode and real M5 data during an open session.
3. Closed-market UI clarity.
4. Final UI polish.

## Market-off observation

13.09.2026 is Sunday. `MARKET_CLOSED`, zero SPOT universe, and absent current LIQ NOW/FLOW are expected. Do not synthesize values.

Observed Futures OI pipeline: 600 raw, 199 active, 233 analyzed, 233 OI available, 224 liquidity available, top 20 returned; turnover uses real MOEX RFUD `VALTODAY`; money flow is `NO_DATA` while closed.

## Mapping defect

Observed: 195 underlying requests, 48 class codes, 147 missing, 48 exact matches, 0 semantic matches, 24.12% coverage. Missing mappings must be classified as supported BASE, futures-only outside BASE, or genuinely unresolved BCS mapping. BCS live metadata is source of truth. No synthetic fallback.

## Rules

REAL DATA ONLY. NO SYNTHETIC VALUES. NO FUTURES AS SPOT SUBSTITUTE. NO FAKE CLASS CODES. NO FAKE TICKERS. NO FAKE LIQUIDITY. NO ORDER EXECUTION. NO PORTFOLIO MANAGEMENT. One application only. Work on `main`.
