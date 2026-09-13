from services.money_flow_service import MoneyFlowService


def _trades():
    return {
        "records": [
            {"side": "BUY", "price": 100.0, "volume": 1000},
            {"side": "BUY", "price": 100.2, "volume": 1200},
            {"side": "BUY", "price": 100.4, "volume": 1500},
            {"side": "BUY", "price": 100.5, "volume": 1800},
            {"side": "BUY", "price": 100.6, "volume": 2200},
            {"side": "SELL", "price": 100.3, "volume": 300},
            {"side": "SELL", "price": 100.2, "volume": 250},
        ]
    }


def test_real_trade_flow_detects_buyer_and_book_alignment():
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
    assert result["money_flow_position_claim"] == "PROBABLE_FLOW_ZONE_ONLY"


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
