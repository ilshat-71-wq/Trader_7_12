# Signal outcome audit (analysis-only)

This module adds a deterministic evaluator for **timestamped signals**. It does not
change live signal generation, radar ranking, cloud market data, or trade execution.

## Contract

- Signal timestamp must be timezone-aware.
- Only candles strictly later than the signal timestamp are considered.
- Only real historical candles supplied by the caller are evaluated; no synthetic
  candles or inferred prices are created.
- Default target is a 1% move in the signal direction. This measures the
  underlying instrument's price move, not return on account equity.
- A signal-provided stop price is used when present; otherwise a stop may be
  supplied explicitly to the evaluator. The evaluator does not invent a stop.
- If target and stop are both touched in one candle, the result is
  `AMBIGUOUS_SAME_BAR`; the evaluator does not assume which happened first.
- MFE/MAE are measured from the entry price over the evaluated bars up to the
  first target/stop/ambiguous bar or the selected horizon.
- Round-trip costs are explicit input in basis points and reported separately.
  This is a simple cost deduction, not a fill simulator. Gaps, spread, queue
  priority, market impact, taxes, margin, and contract multiplier are not modeled.
- Futures outcomes are price-move statistics only until a contract-specific
  capital/P&L model is separately specified.

## Append-only journal

`SignalOutcomeJournal` stores one JSON object per line (JSONL), using append mode,
flush and fsync. The Cloud Market Data Engine appends eligible SPOT scanner observations. The desktop FINAL RADAR also appends a record only when a candidate passes the existing three-scan and realtime gates and appears in the FINAL list, including SPOT and FUTURES. The default path is platform-specific (`~/.local/share/trader_7_12/signal_outcomes.jsonl` in Cloud Engine; `~/Library/Application Support/Trader_7_12/signal_outcomes.jsonl` in the macOS app); set `SIGNAL_OUTCOME_JOURNAL_PATH` to override it. Since these defaults differ, Cloud evaluates its own journal by default; desktop FINAL RADAR outcomes require both processes to share the same journal path. Both captures are audit-only and do not change ranking or trading decisions. The Cloud worker evaluates at most two same-day signal episodes per run, at most once every five minutes, on a daemon thread separate from the live scan. It uses real closed BCS M5 candles, waits for a barrier or the complete 60-bar horizon, and appends one outcome event per episode. Partial history and missing data remain pending, not losses. The default round-trip cost is 10 bps (`SIGNAL_AUDIT_ROUND_TRIP_COST_BPS`). Repeated Cloud snapshots are grouped into a same-day episode and must not be counted as independent trades. FINAL Radar records use scan/instrument/ticker/direction IDs, avoid duplicates while a candidate continuously remains in FINAL, and permit a new observation after it leaves and re-enters.

Current capture event: `signal_observation`, containing the timestamp, entry price, model, direction, probability, class code, scan/snapshot version, phase, FINAL confirmation count, realtime state, and available market context. The Cloud engine schedules a bounded background BCS candle evaluation worker after scans. It checks at most two pending episodes per run, no more often than every five minutes, reads closed M5 candles, and writes an append-only outcome only when a barrier is reached or the full 60-bar horizon has elapsed. Partial history remains pending. Round-trip cost defaults to 10 bps and can be configured with `SIGNAL_AUDIT_ROUND_TRIP_COST_BPS`. The evaluator now also provides `summarize_model_quality`, which compares predicted probability with the observed `TARGET_FIRST` event by instrument/direction/phase and probability bucket, reporting calibration gap and Brier score. It excludes ambiguous and missing-data records rather than guessing.

Do not overwrite signal events with later model values. Keep model version,
snapshot version, instrument type, direction, entry price, and timestamp attached
to each signal.

## API sketch

```python
from services.signal_outcome_audit_service import evaluate_signal, summarize_outcomes, summarize_model_quality

outcome = evaluate_signal(
    signal_record,
    real_future_candles,
    target_pct=1.0,
    stop_pct=None,  # use an explicit signal stop if one exists; otherwise no stop
    max_bars=60,
    round_trip_cost_bps=10.0,
)
report = summarize_outcomes([outcome])
quality = summarize_model_quality([outcome])
```

Candle dictionaries require `time` (timezone-aware ISO timestamp), `high`,
`low`, and `close`. Records with missing/invalid candle data are skipped and
never replaced with estimates.

## Validation

Tests are in `Program/test_signal_outcome_audit_service.py`. They cover timezone
validation, look-ahead exclusion, LONG/SHORT target detection, explicit stop,
ambiguous candles, missing future data, cost deduction, and journal persistence.
Run with the project's normal test environment:

```bash
pytest -q Program/test_signal_outcome_audit_service.py
pytest -q Program
```

This pull request must not be considered production-ready until those commands
pass in the project's actual environment and the live capture wiring is reviewed.
