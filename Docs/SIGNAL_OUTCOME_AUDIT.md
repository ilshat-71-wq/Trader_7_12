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
flush and fsync. The Cloud Market Data Engine now appends eligible SPOT scanner observations to this journal. The default path is `~/.local/share/trader_7_12/signal_outcomes.jsonl`; set `SIGNAL_OUTCOME_JOURNAL_PATH` to override it. The capture is audit-only and does not change ranking or trading decisions. Each scan observation gets its own ID, so repeated observations of the same ticker across scans are correlated and must not be counted as independent trades. The desktop Final Radar and Futures OI candidates are not yet captured by this integration.

Current capture event: `signal_observation`, containing the scanner timestamp, price, model, direction, probability, class code, snapshot version, and available market context. `outcome` events are not yet automatically produced; the next step is the bounded BCS candle evaluation worker.

Do not overwrite signal events with later model values. Keep model version,
snapshot version, instrument type, direction, entry price, and timestamp attached
to each signal.

## API sketch

```python
from services.signal_outcome_audit_service import evaluate_signal, summarize_outcomes

outcome = evaluate_signal(
    signal_record,
    real_future_candles,
    target_pct=1.0,
    stop_pct=None,  # use an explicit signal stop if one exists; otherwise no stop
    max_bars=60,
    round_trip_cost_bps=10.0,
)
report = summarize_outcomes([outcome])
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
