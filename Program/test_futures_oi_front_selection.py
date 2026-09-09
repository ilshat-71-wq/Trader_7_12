from datetime import date

from services.open_interest_service import OpenInterestService
from services.futures_oi_marketdata_scanner_service import FuturesOIMarketDataScannerService


def test_marketdata_family_and_expiry_parse_quarterly_contracts():
    assert OpenInterestService._marketdata_family("ALU6") == "ALRS"
    assert OpenInterestService._marketdata_expiry("ALU6") == date(2026, 9, 1)
    assert OpenInterestService._marketdata_family("ALZ6") == "ALRS"
    assert OpenInterestService._marketdata_expiry("ALZ6") == date(2026, 12, 1)


def test_front_contract_selection_uses_nearest_active_expiry_with_oi():
    rows = [
        {"secid": "ALZ6", "openposition": 1000},
        {"secid": "ALU6", "openposition": 2000},
        {"secid": "ALM7", "openposition": 3000},
        {"secid": "CHU6", "openposition": 500},
        {"secid": "CHZ6", "openposition": 0},
    ]
    selected = OpenInterestService._front_marketdata_rows(rows, as_of=date(2026, 9, 9))
    assert selected["ALRS"]["secid"] == "ALU6"
    assert selected["CHMF"]["secid"] == "CHU6"


def test_front_selection_does_not_call_every_contract_individually():
    service = OpenInterestService(http_get=lambda *args, **kwargs: {
        "marketdata": {
            "columns": ["SECID", "OPENPOSITION"],
            "data": [["ALU6", 2000], ["ALZ6", 1000]],
        }
    })
    selected = service.marketdata_front_contracts(as_of=date(2026, 9, 9))
    assert selected["ALRS"]["secid"] == "ALU6"


def test_family_to_underlying_uses_moex_prefix_mapping():
    assert FuturesOIMarketDataScannerService._family_to_underlying("ALRS") == "ALRS"
    assert FuturesOIMarketDataScannerService._family_to_underlying("SBRF") == "SBER"
    assert FuturesOIMarketDataScannerService._family_to_underlying("Si") == "SI"
