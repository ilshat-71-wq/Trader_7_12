# TRADER_7_12 PRO — NEW CHAT STATE / HANDOFF

**Состояние на:** 13.09.2026  
**Repo:** `ilshat-71-wq/Trader_7_12`  
**Branch:** `main`

## Verified sync

Before this handoff, local `main`, `origin/main`, and the running app were verified from commit `d51f9405fc3e36ddb0f42275585a3dcc73882a0e`; local working tree was clean. The handoff update itself is now committed on `main`.

## Current market-off diagnostic

13.09.2026 is Sunday. `SPOT / MARKET RADAR = MARKET_CLOSED`, `universe_total=0`, and absent current `LIQ NOW / FLOW` are expected. Do not synthesize closed-market values.

Futures pipeline observed: 600 raw contracts, 199 active, 233 analyzed, 233 OI available, 224 liquidity available, top 20 returned; turnover source is real MOEX RFUD `VALTODAY`; money flow is `NO_DATA` because the market is closed.

## P0 — mapping

Current underlying mapping is incomplete:
- requested 195
- class codes 48
- missing 147
- exact matches 48
- semantic matches 0
- coverage 24.12%

The 147 missing entries must be truthfully classified as:
A. supported BASE requiring BASE Δ%;
B. futures-only outside BASE;
C. genuinely unresolved BCS mapping.

BCS live metadata remains source of truth. Catalog is lookup assistance only. No synthetic class codes/tickers/quotes/liquidity.

## Work order without live market

1. Inspect mapping/catalog/metadata code.
2. Improve deterministic canonical family → economic underlying → BCS lookup → real instrument acceptance.
3. Add regression tests for canonical futures families and known aliases.
4. Make missing mapping diagnostics explicit and truthful.
5. Review BASE Δ% path for supported mapped BASE instruments.
6. Polish closed-market UI and existing tables without adding architecture layers.
7. Run pytest/build locally.
8. Validate live-market mapping/BASE Δ%/RS/M5/LIQ NOW/FLOW on the next session.

## Rules

REAL DATA ONLY. NO SYNTHETIC VALUES. NO FUTURES AS SPOT SUBSTITUTE. NO FAKE CLASS CODES. NO FAKE TICKERS. NO FAKE LIQUIDITY. NO ORDER EXECUTION. NO PORTFOLIO MANAGEMENT. One application only; work on `main`.
