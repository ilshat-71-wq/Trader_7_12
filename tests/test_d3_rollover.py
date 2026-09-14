from datetime import date
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Program"))

from services.open_interest_service import OpenInterestService


class D3RolloverTests(unittest.TestCase):
    def setUp(self):
        self.svc = OpenInterestService(http_get=lambda *args, **kwargs: {})
        expiry = {"SIU6": date(2026, 9, 17), "SIZ6": date(2026, 12, 17)}
        self.svc._expiry_calendar_cache = {
            day.isoformat(): dict(expiry)
            for day in (
                date(2026, 9, 13), date(2026, 9, 14),
                date(2026, 9, 15), date(2026, 9, 16),
            )
        }
        self.svc._marketdata_all_cache = [
            {"secid": "SIU6", "openposition": 100},
            {"secid": "SIZ6", "openposition": 100},
        ]

    def test_front_before_d3(self):
        selected = self.svc.marketdata_front_contracts(date(2026, 9, 13))
        self.assertEqual(selected["SI"]["secid"], "SIU6")

    def test_rollover_from_d3(self):
        for day in (date(2026, 9, 14), date(2026, 9, 15), date(2026, 9, 16)):
            item = self.svc.marketdata_front_contracts(day)["SI"]
            self.assertEqual(item["secid"], "SIZ6")
            self.assertTrue(item["_moex_rollover_active"])
            self.assertEqual(item["_moex_front_contract"], "SIU6")

    def test_no_next_contract_excludes_family(self):
        self.svc._marketdata_all_cache = [{"secid": "SIU6", "openposition": 100}]
        self.assertNotIn("SI", self.svc.marketdata_front_contracts(date(2026, 9, 14)))

    def test_missing_exact_expiry_is_not_inferred(self):
        self.svc._expiry_calendar_cache["2026-09-15"] = {}
        self.assertNotIn("SI", self.svc.marketdata_front_contracts(date(2026, 9, 15)))


if __name__ == "__main__":
    unittest.main()
