# TRADER_7_12 PRO — SCAN PERFORMANCE PLAN

## Goal

Reduce one normal scanner run from the observed ~4 minutes to a practical **20–30 seconds**, without weakening the SPOT-first selection logic or changing the user's trading workflow.

## Target

- **≤ 30 s** — required normal target.
- **15–25 s** — preferred operating range.
- **> 30 s** — considered slow and requires investigation.
- The scanner must not silently spend minutes retrying one unavailable BCS request.

## What can be prepared without a live BCS session

### 1. Measure every stage

`Program/services/scan_performance_service.py` provides a dependency-free timing/reporting primitive. It is safe to use in offline tests and does not alter market decisions.

Recommended stage names:

1. `UNIVERSE`
2. `MAPPING`
3. `SPOT_RADAR`
4. `H1_STRUCTURE`
5. `SESSION_MONEY`
6. `FUTURES_CONFIRMATION`
7. `RANKING`
8. `UI_RENDER`

The next live run should report total time and stage timings so optimization is based on actual latency rather than guesses.

### 2. Remove duplicate historical requests

Current architecture has several layers that can request the same SPOT history during one scan. The most important optimization target is to reuse the same loaded D/H1/M5 data within a scan instead of requesting it repeatedly.

Known duplication to address:

- daily SPOT candles are used by trend, historical money average and relative strength;
- SPOT M5 candles are used by setup analysis;
- H1 SPOT candles are used for structural context;
- the futures radar layer and the dedicated SPOT setup layer should share the same history service/cache.

### 3. Cache stable data

Safe candidates:

- futures/SPOT mapping — already cached for 300 seconds;
- completed daily candles — short-lived cache, because they do not change during the session;
- completed daily average money — derived from the same cached D candles;
- benchmark D candles — already cached by the radar;
- H1 candles — short-lived cache during repeated scans;
- M5 session candles — very short cache so repeated calls inside one scan reuse the same response.

Current-session M5 data must remain fresh enough for the user's scanner; caching must never turn the radar into a stale historical snapshot.

### 4. Parallelize independent SPOT groups

The current radar processes unique SPOT groups sequentially. Once the data/cache boundary is clean, independent SPOT groups can be evaluated with a small bounded worker pool.

The intended design is **bounded concurrency**, not an unrestricted request flood. This protects BCS from unnecessary load and reduces the effect of one slow instrument on the whole scan.

### 5. Keep retries from dominating the scan

Repeated `SSLError` retries were visible in live runs. The scanner must keep a bounded retry/timeout policy so one unavailable request cannot turn a normal scan into a multi-minute wait.

The exact timeout/retry values should be validated with BCS during the next live run rather than guessed offline.

## What must NOT change during optimization

- SPOT remains the source of market idea and structure.
- H1 remains the primary SPOT structural context.
- M5 remains the session formation layer.
- First pullback/rebound is measured on SPOT, never futures.
- The user trades futures; the radar selects the practical futures implementation.
- BMU6 → BRENT1026 remains the canonical mapping regression.
- Current SPOT money/activity remains more important than raw futures turnover.
- No automatic orders, entry commands, position sizing, SL/TP or execution are added.

## Next live validation

Run the scanner once when MOEX is open and record:

- total scan time;
- number of BCS requests;
- number of retries/errors;
- time spent on mapping;
- time spent on SPOT radar;
- time spent on H1/M5 structure;
- time spent on futures confirmation.

Only after this measurement should concurrency and timeout values be tuned against the real BCS response behavior.

## Offline checkpoint

The performance timing service and its regression tests are now stored in the repository. The actual network-latency reduction requires one live BCS run for validation and tuning.
