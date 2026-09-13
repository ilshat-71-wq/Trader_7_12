from datetime import datetime, timezone

from services.money_flow_service import MoneyFlowService


def _trades():
    return {
        "records": [
            {"side": "BUY", "price": 100.0, "volume": 1000, "dateTime": "2026-09-10T12:55:00Z"},
            {"side": "BUY", "price": 100.2, "volume": 1200, "dateTime": "2026-09-10T12:56:00Z"},
            {"side": "BUY", "price": 100.4, "volume": 1500, "dateTime": "2026-09-10T12:57:00Z"},
            {"side": "BUY", "price": 100.5, "volume": 1800, "dateTime": "2026-09-10T12:58:00Z"},
            {"side": "BUY", "price": 100.6, "volume": 2200, "dateTime": "2026-09-10T12:59:00Z"},
            {"side": "SELL", "price": 100.3, "volume": 300, "dateTime": "2026-09-10T12:55:30Z"},
            {"side": "SELL", "price": 100.2, "volume": 250, "dateTime": "2026-09-10T12:56:30Z"},
        ]
    }


def test_real_trade_flow_detects_buyer_and_book_alignment(monkeypatch):
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, 10, 13, 0, tzinfo=timezone.utc)

    monkeypatch.setattr("services.money_flow_service.datetime", FixedDateTime)
    result = MoneyFlowService.analyze_snapshot(
        "SBER",
        "TQBR",
        _trades(),
        {"bidVolume": 9000, "askVolume": 3000},
    )

    assert result["money_flow_status"] == "AVAILABLE"
    assert result["money_flow_signal"] in {"ACCUMULATION", "BUYER_ACTIVE", "BUY_ABSORPTION"}
    assert result["money_flow_delta"] > 0
    assert result["money_flow_book_imbalance_pct"] > 0
    assert result["money_flow_book_aligned"] is True
    assert result["money_flow_zone_low"] == 100.0
    assert result["money_flow_zone_high"] == 100.6
    assert result["money_flow_recent_total"] > 0
    assert result["money_flow_liquidity_state"] == "HOT"
    assert result["money_flow_liquidity_direction"] == "BUY"
    assert result["money_flow_position_claim"] == "PROBABLE_FLOW_ZONE_ONLY"


def test_position_interpretation_uses_price_and_oi_without_claiming_identity():
    item = {
        "change_percent": 1.8,
        "money_flow_delta_pct": 28.0,
        "money_flow_signal": "ACCUMULATION",
        "oi_analysis": {"oi_change_percent": 4.0},
    }
    action, confidence = MoneyFlowService._position_interpretation(item)
    assert action == "LONG_BUILDUP"
    assert confidence == "HIGH"


def test_position_interpretation_distinguishes_short_buildup():
    item = {
        "change_percent": -1.4,
        "money_flow_delta_pct": -24.0,
        "money_flow_signal": "SELLER_ACTIVE",
        "oi_analysis": {"oi_change_percent": 3.0},
    }
    action, confidence = MoneyFlowService._position_interpretation(item)
    assert action == "SHORT_BUILDUP"
    assert confidence == "HIGH"


def test_no_trades_never_creates_synthetic_signal():
    result = MoneyFlowService.analyze_snapshot(
        "SBER",
        "TQBR",
        {"records": []},
        {"bidVolume": 100000, "askVolume": 1000},
    )

    assert result["money_flow_status"] == "NO_DATA"
    assert result["money_flow_signal"] == "NO_DATA"
    assert result["money_flow_confidence"] == "LOW"
