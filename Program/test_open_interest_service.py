from services.open_interest_service import OpenInterestService


def test_classify_price_up_oi_up():
    result = OpenInterestService.classify(1.2, 3.0, volume_percent=25.0, oi_zscore=2.2)
    assert result["oi_regime"] == "NEW_POSITION_BUILDING_UP"
    assert result["oi_strength"] == "STRONG"
    assert result["volume_confirmation"] is True


def test_classify_price_up_oi_down():
    result = OpenInterestService.classify(1.0, -2.0)
    assert result["oi_regime"] == "SHORT_COVERING"


def test_classify_price_down_oi_up():
    result = OpenInterestService.classify(-1.0, 2.0)
    assert result["oi_regime"] == "NEW_POSITION_BUILDING_DOWN"


def test_classify_price_down_oi_down():
    result = OpenInterestService.classify(-1.0, -2.0)
    assert result["oi_regime"] == "LONG_LIQUIDATION"


def test_zscore():
    z = OpenInterestService.zscore(5.0, [1.0, 2.0, 3.0, 4.0, 4.0])
    assert z is not None
    assert z > 0


def test_parse_and_aggregate_futoi():
    payload = {
        "futoi": {
            "columns": ["ticker", "clgroup", "pos", "pos_long", "pos_short"],
            "data": [
                ["Si", "FIZ", 100, 150, -50],
                ["Si", "YUR", -100, 50, -150],
            ],
        }
    }
    rows = OpenInterestService._parse_block(payload)
    result = OpenInterestService._aggregate_rows(rows)
    assert result["ticker"] == "SI"
    assert result["oi"] == 200
