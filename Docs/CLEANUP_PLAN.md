# Trader_7_12 Pro — cleanup checkpoint

This branch is being reduced to the scanner-only architecture:

Futures Universe → Futures/SPOT Mapping → SPOT Radar → Market Relative Strength → Setup/Levels → Futures Confirmation → TOP 2–3.

No portfolio management, position sizing, SL/TP generation, trade execution, or legacy signal/decision engines belong to the active scanner.

Sunday 2026-08-16: no live trading. Monday morning validation is performed from 07:00 Moscow time.

## Benchmark rule
The market benchmark must be the full-return market index represented by IMOEX2 / IRUS2. Ordinary IMOEX or IMOEXF must not silently replace it. If the required benchmark metadata/candles are unavailable, RS must be reported as unavailable.
