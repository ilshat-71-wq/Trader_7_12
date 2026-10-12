from datetime import datetime, timezone

import pytest

from services.signal_outcome_audit_service import (
    SignalOutcomeJournal,
    evaluate_signal,
    normalize_signal,
    summarize_outcomes,
    summarize_model_quality,
)


def _signal(direction="LONG", **extra):
    row = {
        "ticker": "TEST",
        "instrument_type": "SPOT",
        "direction": direction,
        "signal_time": "2026-10-12T10:00:00+03:00",
        "entry_price": 100.0,
        "signal_model": "test-v1",
    }
    row.update(extra)
    return row


def _candle(time, high, low, close):
    return {"time": time, "high": high, "low": low, "close": close}


def test_normalize_signal_requires_timezone_aware_timestamp():
    with pytest.raises(ValueError, match="timezone"):
        normalize_signal(_signal(signal_time="2026-10-12T10:00:00"))


def test_ignores_candles_at_or_before_signal_time():
    rows = [
        _candle("2026-10-12T09:59:00+03:00", 103, 99, 102),
        _candle("2026-10-12T10:00:00+03:00", 103, 99, 102),
    ]
    result = evaluate_signal(_signal(), rows)
    assert result["outcome"] == "NO_FUTURE_DATA"
    assert result["bars_evaluated"] == 0


def test_long_target_first_and_costs_are_separate():
    rows = [_candle("2026-10-12T10:05:00+03:00", 101.2, 99.8, 101.1)]
    result = evaluate_signal(_signal(), rows, target_pct=1, round_trip_cost_bps=10)
    assert result["outcome"] == "TARGET_FIRST"
    assert result["gross_return_pct"] == 1.0
    assert result["net_return_pct"] == 0.9
    assert result["mfe_pct"] == 1.2


def test_short_target_first_uses_low_barrier():
    rows = [_candle("2026-10-12T10:05:00+03:00", 100.2, 98.8, 99.0)]
    result = evaluate_signal(_signal("SHORT"), rows, target_pct=1)
    assert result["outcome"] == "TARGET_FIRST"
    assert result["target_price"] == 99.0


def test_same_bar_target_and_stop_is_not_guessed():
    rows = [_candle("2026-10-12T10:05:00+03:00", 102, 98, 100)]
    result = evaluate_signal(_signal(stop_price=99.0), rows, target_pct=1)
    assert result["outcome"] == "AMBIGUOUS_SAME_BAR"
    assert result["gross_return_pct"] is None
    assert result["net_return_pct"] is None


def test_stop_first_is_reported():
    rows = [_candle("2026-10-12T10:05:00+03:00", 100.4, 98.8, 99.0)]
    result = evaluate_signal(_signal(stop_price=99.0), rows, target_pct=1)
    assert result["outcome"] == "STOP_FIRST"
    assert result["gross_return_pct"] == -1.0


def test_missing_future_data_is_not_counted_as_failure_or_win():
    result = evaluate_signal(_signal(), [])
    summary = summarize_outcomes([result])
    assert summary["overall"]["no_future_data"] == 1
    assert summary["overall"]["evaluated"] == 0
    assert summary["overall"]["target_first_pct"] is None


def test_journal_appends_and_reads_jsonl(tmp_path):
    journal = SignalOutcomeJournal(tmp_path / "audit" / "signals.jsonl")
    journal.append({"event": "signal", "ticker": "SBER"})
    journal.append({"event": "outcome", "ticker": "SBER"})
    assert [x["event"] for x in journal.read_all()] == ["signal", "outcome"]



def test_model_quality_calibration_excludes_ambiguous_and_missing_outcomes():
    rows = [
        {"instrument_type": "SPOT", "direction": "LONG", "phase": "DEVELOPING",
         "signal_probability": 90.0, "outcome": "TARGET_FIRST"},
        {"instrument_type": "SPOT", "direction": "LONG", "phase": "DEVELOPING",
         "signal_probability": 90.0, "outcome": "STOP_FIRST"},
        {"instrument_type": "FUTURES", "direction": "SHORT", "phase": "OI_FLOW",
         "signal_probability": 95.0, "outcome": "AMBIGUOUS_SAME_BAR"},
        {"instrument_type": "SPOT", "direction": "SHORT", "phase": "START",
         "signal_probability": 92.0, "outcome": "NO_FUTURE_DATA"},
    ]
    report = summarize_model_quality(rows)
    assert report["records_seen"] == 4
    assert report["resolved"] == 2
    assert report["excluded"] == 2
    assert report["overall"]["target_first"] == 1
    assert report["overall"]["observed_target_rate_pct"] == 50.0
    assert report["overall"]["mean_predicted_probability_pct"] == 90.0
    assert report["overall"]["calibration_gap_pp"] == 40.0
    assert report["overall"]["brier_score"] == 0.41
    assert list(report["by_instrument_direction_phase"]) == ["SPOT:LONG:DEVELOPING"]
