# TRADER_7_12 PRO — NEW CHAT STATE / HANDOFF

**Состояние на:** 13.09.2026  
**Repo:** `ilshat-71-wq/Trader_7_12`  
**Branch:** `main`  
**Verified local/remote commit before this handoff:** `d51f9405fc3e36ddb0f42275585a3dcc73882a0e`

## Current verified state

- Local branch = `main`.
- Local `HEAD` = `d51f9405fc3e36ddb0f42275585a3dcc73882a0e`.
- `origin/main` = `d51f9405fc3e36ddb0f42275585a3dcc73882a0e`.
- Local working tree is clean.
- macOS application builds and launches successfully from this state.
- Production app: `~/Applications/Trader_7_12 Pro.app`.
- `dist/Trader_7_12 Pro.app` points to the production app.

## Today’s market-off diagnostic

13.09.2026 is Sunday. Therefore `SPOT / MARKET RADAR = MARKET_CLOSED`, `universe_total=0`, and current `LIQ NOW / FLOW` absence are expected and must not be treated as synthetic-data or scanner failures.

Futures pipeline observed:
- raw contracts: 600
- active contracts: 199
- analyzed: 233
- OI available: 233
- liquidity available: 224
- top liquidity returned: 20
- turnover source: real MOEX RFUD `VALTODAY`
- money flow: `NO_DATA` because the market is closed

## Current P0

Underlying mapping remains the main technical defect:
- underlying requested: 195
- underlying class codes: 48
- missing class codes: 147
- exact matches: 48
- semantic matches: 0
- coverage: 24.12%

The 147 missing mappings must be classified into:
A. supported BASE requiring BASE Δ%;
B. futures-only outside BASE;
C. genuinely unresolved BCS mapping.

No synthetic fallback is permitted.

## Next work without live market

1. Inspect and improve BCS underlying mapping using repository code/catalog and real BCS metadata rules.
2. Add/strengthen deterministic mapping tests for canonical futures families and aliases.
3. Ensure missing mappings are classified truthfully rather than silently becoming `NO_CLASS_CODE`.
4. Review BASE Δ% request path so every supported mapped BASE instrument can obtain real BCS classCode and `07:00→NOW` M5 candles during an open session.
5. Review closed-market UI state so it clearly explains that missing live SPOT/FLOW data is expected when the market is closed.
6. Review final UI polish without adding new applications, mini-scanners, branches, or architecture layers.
7. Run pytest and build locally after code changes.
8. On the next trading session, use a real scan to validate mapping coverage, BASE Δ%, M5, RS, LIQ NOW and FLOW.

## Non-negotiable rules

REAL DATA ONLY. NO SYNTHETIC VALUES. NO FUTURES AS SPOT SUBSTITUTE. NO FAKE CLASS CODES. NO FAKE TICKERS. NO FAKE LIQUIDITY. NO ORDER EXECUTION. NO PORTFOLIO MANAGEMENT.

Never restart the project. Work directly on `main` unless a temporary branch is explicitly requested.
