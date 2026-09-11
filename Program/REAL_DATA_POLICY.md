# REAL DATA POLICY

Trader_7_12 uses real, traceable market data only.

1. Missing data is missing data. It is never converted to GREEN, OK, zero, or a synthetic value.
2. A fallback is valid only when the passport explicitly permits another real source.
3. Futures are never substituted for a required spot/base instrument.
4. A calculation is valid only when every required input is real and present.
5. API, SSL, timeout, parsing, coverage, and mapping failures remain explicit diagnostics.
6. UI must display backend data status without changing qualification, ranking, calculations, or values.
7. Automated tests must verify failure states as well as successful states.
8. GREEN means the checked condition is actually satisfied; it does not mean that the program merely continued running.

This policy applies to every scanner, service, file, metric, diagnostic, and UI in Trader_7_12.
