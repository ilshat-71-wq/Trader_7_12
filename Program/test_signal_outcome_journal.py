from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from services.signal_outcome_journal import SignalOutcomeJournal

MSK = ZoneInfo("Europe/Moscow")


def test_journal_deduplicates_final_candidate_per_day(tmp_path):
    journal = SignalOutcomeJournal(tmp_path / "outcomes.sqlite3")
    now = datetime(2026, 10, 13, 10, 0, tzinfo=MSK)
    row = {
        "final_ticker": "SBER", "final_instrument_type": "SPOT",
        "signal": "LONG", "price": 100.0, "spot_class_code": "TQBR",
        "signal_probability": 93.2, "move_phase": "START",
    }
    assert journal.record_candidates([row], now=now) == 1
    assert journal.record_candidates([row], now=now + timedelta(minutes=5)) == 0
    assert len(journal.records()) == 1


def test_missing_real_price_or_class_code_is_not_fabricated(tmp_path):
    journal = SignalOutcomeJournal(tmp_path / "outcomes.sqlite3")
    now = datetime(2026, 10, 13, 10, 0, tzinfo=MSK)
    journal.record_candidates([{
        "final_ticker": "SBER", "final_instrument_type": "SPOT",
        "signal": "LONG", "signal_probability": 90.0,
    }], now=now)
    record = journal.records()[0]
    assert record["entry_price"] is None
    assert record["status"] == "INCOMPLETE_DATA"
    assert record["data_reason"] == "ENTRY_PRICE_MISSING_OR_INVALID"


def test_real_candle_evaluation_calculates_mfe_mae_and_optional_net(tmp_path):
    journal = SignalOutcomeJournal(tmp_path / "outcomes.sqlite3")
    entry = datetime(2026, 10, 13, 10, 0, tzinfo=MSK)
    journal.record_candidates([{
        "final_ticker": "SBER", "final_instrument_type": "SPOT",
        "signal": "LONG", "price": 100.0, "spot_class_code": "TQBR",
        "signal_probability": 92.0, "move_phase": "START",
    }], now=entry)
    candles = []
    for i in range(12):
        stamp = entry + timedelta(minutes=5 * i)
        candles.append({
            "time": stamp.isoformat(), "open": 100.0,
            "high": 101.0 + i * 0.1, "low": 99.5,
            "close": 100.2 + i * 0.1, "volume": 1000,
        })
    now = entry + timedelta(minutes=65)
    assert journal.evaluate_pending(
        lambda ticker, code, start, end: candles,
        now=now, costs_bps=10.0,
    ) == 1
    record = journal.records()[0]
    assert record["status"] == "COMPLETE"
    assert record["outcomes"]["5"]["source"] == "BCS_CLOSED_M5"
    assert record["outcomes"]["5"]["mfe_pct"] > 0
    assert record["outcomes"]["5"]["mae_pct"] > 0
    assert record["outcomes"]["5"]["net_close_return_pct"] is not None


def test_net_return_is_not_claimed_without_cost_assumption(tmp_path):
    journal = SignalOutcomeJournal(tmp_path / "outcomes.sqlite3")
    entry = datetime(2026, 10, 13, 10, 0, tzinfo=MSK)
    journal.record_candidates([{
        "final_ticker": "SBER", "final_instrument_type": "SPOT",
        "signal": "LONG", "price": 100.0, "spot_class_code": "TQBR",
    }], now=entry)
    candles = [{
        "time": entry.isoformat(), "high": 101.0, "low": 99.0, "close": 100.5
    }]
    journal.evaluate_pending(
        lambda ticker, code, start, end: candles,
        now=entry + timedelta(minutes=65),
    )
    assert journal.records()[0]["outcomes"]["5"]["net_close_return_pct"] is None



def test_incomplete_record_can_be_repaired_by_later_real_data(tmp_path):
    journal = SignalOutcomeJournal(tmp_path / "outcomes.sqlite3")
    entry = datetime(2026, 10, 13, 10, 0, tzinfo=MSK)
    base = {
        "final_ticker": "SBER", "final_instrument_type": "SPOT",
        "signal": "LONG", "signal_probability": 91.0,
    }
    journal.record_candidates([base], now=entry)
    repaired = dict(base, price=100.0, spot_class_code="TQBR")
    assert journal.record_candidates([repaired], now=entry + timedelta(minutes=1)) == 1
    record = journal.records()[0]
    assert record["status"] == "PENDING"
    assert record["entry_price"] == 100.0


def test_late_cost_configuration_updates_existing_net_outcome(tmp_path):
    journal = SignalOutcomeJournal(tmp_path / "outcomes.sqlite3")
    entry = datetime(2026, 10, 13, 10, 0, tzinfo=MSK)
    journal.record_candidates([{
        "final_ticker": "SBER", "final_instrument_type": "SPOT",
        "signal": "LONG", "price": 100.0, "spot_class_code": "TQBR",
    }], now=entry)
    candles = [{
        "time": entry.isoformat(), "high": 101.0, "low": 99.0, "close": 100.5
    }]
    loader = lambda ticker, code, start, end: candles
    journal.evaluate_pending(loader, now=entry + timedelta(minutes=65))
    assert journal.records()[0]["outcomes"]["5"]["net_close_return_pct"] is None
    journal.evaluate_pending(loader, now=entry + timedelta(minutes=65), costs_bps=10.0)
    assert journal.records()[0]["outcomes"]["5"]["net_close_return_pct"] == 0.4
