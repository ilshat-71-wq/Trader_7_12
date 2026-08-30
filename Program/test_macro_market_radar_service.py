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


def test_intraday_proxy_direction_uses_first_and_last_trade():
    class FakeAPI:
        def get_last_trades(self, ticker, class_code):
            return {
                "records": [
                    {"dateTime": "2026-08-30T07:00:00Z", "price": 100.0, "quantity": 2},
                    {"dateTime": "2026-08-30T07:10:00Z", "price": 101.0, "quantity": 3},
                ]
            }

    radar = MacroMarketRadarService(api=FakeAPI())
    result = radar._direct_trade_snapshot("TEST", "SPBFUT")

    assert result["direction"] == "LONG"
    assert round(result["change_percent"], 4) == 1.0
    assert result["trade_count"] == 2
    assert result["trade_money"] == 503.0


def test_intraday_proxy_returns_none_without_two_valid_trades():
    class FakeAPI:
        def get_last_trades(self, ticker, class_code):
            return {"records": [{"price": 100.0}]}

    radar = MacroMarketRadarService(api=FakeAPI())
    assert radar._direct_trade_snapshot("TEST", "SPBFUT") is None
