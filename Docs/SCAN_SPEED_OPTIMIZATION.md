# Trader_7_12 Pro — Scan Speed Optimization

## Target

Normal live scan target: **20–30 seconds**.

The optimization must remove avoidable network repetition and long retry waits without weakening the SPOT-first analytical model.

## Implemented in this checkpoint

### 1. Fail-fast HTTP defaults

`Program/api/request_helper.py` now uses:

- one attempt by default;
- 0.2 s retry delay when an explicit second attempt is requested;
- 8 s request timeout;
- per-call timeout/retry overrides remain available.

A transient BCS problem therefore cannot silently consume several minutes through repeated 15-second waits.

### 2. SPOT metadata cache

`FuturesSpotMappingService` caches each instrument-type response for 5 minutes inside the running application.

This prevents repeated scans from re-downloading the same STOCK/CURRENCY/GOODS/COMMODITY/METALS/INDICES metadata.

### 3. Parallel SPOT metadata loading

Independent instrument-type requests use a bounded `ThreadPoolExecutor` with at most four workers.

A failed type is skipped while the remaining types continue, instead of serially blocking the entire mapping stage.

## Preserved behavior

- SPOT remains the source of market structure and setup.
- H1 remains the primary SPOT structural timeframe.
- M5 remains the session formation layer.
- FUTURES remain the tradable instruments.
- BCS/MOEX underlying metadata remains authoritative for mapping.
- `BMU6 → BRENT1026` remains canonical.
- No automatic entries or orders are introduced.

## Next live validation

Run the scanner and record:

- total scan time;
- number of `Retry` lines;
- instrument metadata calls;
- trade collection duration;
- whether the result still contains the same top candidates.

If the first live scan is still above 30 seconds, the next target is shared candle/history caching and bounded concurrency for independent SPOT/futures data requests.
