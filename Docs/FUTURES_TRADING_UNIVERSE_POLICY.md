# Trader_7_12 Pro — Locked Futures Trading Universe

**Effective:** 15.09.2026

This policy is a production boundary for Futures OI. It is deliberately narrower than the full MOEX derivatives catalogue.

## Allowed

- Russian single-stock futures;
- dated USD/RUB futures;
- dated EUR/RUB futures;
- dated CNY/RUB futures;
- Brent;
- Light Sweet Crude Oil;
- Natural Gas;
- Gold.

## Forbidden

- perpetual / daily-auto-roll futures;
- crypto futures;
- foreign single-stock futures;
- foreign ETF futures;
- foreign FX futures;
- index futures;
- interest-rate futures;
- other commodities outside the declared scope;
- unknown/new products not explicitly admitted by the policy.

## Rules

1. The contract must be a dated MOEX futures contract.
2. Russian stock futures are admitted only when the economic underlying is in the project's explicit Russian-stock universe.
3. Currency/commodity admission is limited to the declared families.
4. Products outside this policy are removed before OI, liquidity, money-flow and signal processing.
5. Excluded products must not be counted as BASE-underlying mapping failures.
6. No synthetic ticker, classCode, price, OI, liquidity or underlying is ever created.
7. MOEX remains the source of truth for futures identity and expiry; BCS remains the source of truth for real instrument ticker/classCode and market data.

Implementation: `Program/services/futures_trading_universe_policy.py`.
