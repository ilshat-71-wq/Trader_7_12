from datetime import date

from services.open_interest_service import OpenInterestService


class FakeHTTP:
    def __init__(self):
        self.urls = []

    def __call__(self, url, timeout=8):
        self.urls.append(url)
        if "analyticalproducts/futoi" in url:
            return {"futoi": {"columns": ["ticker", "pos"], "data": []}}
        return {
            "marketdata": {
                "columns": ["SECID", "OPENPOSITION", "OICHANGE", "TRADEDATE"],
                "data": [
                    ["SBRF-12.26", 1000, 10, "2026-09-08"],
                    ["SBRF-9.26", 2000, -20, "2026-09-08"],
                    ["GAZR-9.26", 3000, 30, "2026-09-08"],
                ],
            }
        }


def test_marketdata_family_fallback_selects_front_contract_and_oi():
    http = FakeHTTP()
    service = OpenInterestService(http_get=http)

    result = service.analyze("SR", 1.0, as_of=date(2026, 9, 8))

    assert result["oi_status"] == "AVAILABLE"
    assert result["oi_source"] == "MOEX_FUTURES_MARKETDATA"
    assert result["oi_contract_ticker"] == "SBRF-9.26"
    assert result["oi"] == 2000
    assert result["oi_change_contracts"] == -20
    assert result["oi_change_percent"] < 0


def test_marketdata_family_fallback_supports_second_root():
    service = OpenInterestService(http_get=FakeHTTP())

    result = service.analyze("GZ", -1.0, as_of=date(2026, 9, 8))

    assert result["oi_source"] == "MOEX_FUTURES_MARKETDATA"
    assert result["oi_contract_ticker"] == "GAZR-9.26"
    assert result["oi"] == 3000
