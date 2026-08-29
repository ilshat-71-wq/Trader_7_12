from datetime import date, timedelta

from services.macro_market_radar_service import MacroMarketRadarService


def future(ticker, group_expiry):
    return {
        "ticker": ticker,
        "classCode": "SPBFUT",
        "expiry": group_expiry,
        "name": ticker,
    }


def test_macro_universe_covers_all_four_groups():
    far = (date.today() + timedelta(days=20)).isoformat()
    futures = [
        future("BRV6", far),
        future("GLZ6", far),
        future("NGV6", far),
        future("SiZ6", far),
        future("SBERU6", far),
    ]
    result = MacroMarketRadarService.build_universe(futures)
    groups = {item["spot_group"] for item in result}
    assert groups == {"OIL", "GOLD", "GAS", "USDRUB"}


def test_macro_universe_rejects_contracts_too_close_to_expiry():
    near = (date.today() + timedelta(days=2)).isoformat()
    futures = [future("BRV6", near)]
    assert MacroMarketRadarService.build_universe(futures) == []


def test_macro_universe_marks_direct_analysis_explicitly():
    far = (date.today() + timedelta(days=20)).isoformat()
    result = MacroMarketRadarService.build_universe([future("SiZ6", far)])
    assert result[0]["analysis_source"] == "FUTURES_DIRECT"
    assert result[0]["spot_group"] == "USDRUB"
