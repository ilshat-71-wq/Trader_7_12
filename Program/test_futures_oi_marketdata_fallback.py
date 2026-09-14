from datetime import date
from urllib.parse import urlparse

from services.open_interest_service import OpenInterestService


class FakeHTTP:
    def __init__(self):
        self.urls = []

    def __call__(self, url, timeout=8):
        self.urls.append(url)
        if "analyticalproducts/futoi" in url:
            return {"futoi": {"columns": ["ticker", "pos"], "data": []}}

        rows = [
            ["SBRF-12.26", 1000, 10, "2026-09-08"],
            ["SBRF-9.26", 2000, -20, "2026-09-08"],
            ["GAZR-9.26", 3000, 30, "2026-09-08"],
        ]
        path_parts = [part for part in urlparse(url).path.split("/") if part]
        requested = path_parts[-1].removesuffix(".json").upper() if path_parts else ""
        if requested and requested != "SECURITIES":
            rows = [row for row in rows if row[0].upper() == requested]

        return {
            "marketdata": {
                "columns": ["SECID", "OPENPOSITION", "OICHANGE", "TRADEDATE"],
                "data": rows,
            },
        }


def _marketdata_rows(service, as_of):
    rows = service._load_marketdata_all()
    service._expiry_calendar_cache[as_of.isoformat()] = {
        "SBRF-9.26": date(2026, 9, 17),
        "SBRF-12.26": date(2026, 12, 17),
        "GAZR-9.26": date(2026, 9, 17),
    }
    return service._working_marketdata_rows(rows, as_of=as_of)


def test_marketdata_family_fallback_selects_front_contract_and_oi():
    service = OpenInterestService(http_get=FakeHTTP())
    as_of = date(2026, 9, 8)
    selected = _marketdata_rows(service, as_of)
    row = selected["SBRF"]
    analysis = service._marketdata_analysis(
        row["secid"], "SBRF", 1.0, None
    )

    assert analysis["oi_status"] == "AVAILABLE"
    assert analysis["oi_source"] == "MOEX_FUTURES_MARKETDATA"
    assert analysis["oi_contract_ticker"] == "SBRF-9.26"
    assert analysis["oi"] == 2000
    assert analysis["oi_change_contracts"] == -20
    assert analysis["oi_change_percent"] < 0


def test_marketdata_family_fallback_supports_second_root():
    service = OpenInterestService(http_get=FakeHTTP())
    as_of = date(2026, 9, 8)
    selected = _marketdata_rows(service, as_of)
    row = selected["GAZR"]
    analysis = service._marketdata_analysis(
        row["secid"], "GAZR", -1.0, None
    )

    assert analysis["oi_source"] == "MOEX_FUTURES_MARKETDATA"
    assert analysis["oi_contract_ticker"] == "GAZR-9.26"
    assert analysis["oi"] == 3000
