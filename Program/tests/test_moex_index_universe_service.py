import unittest

from services.moex_index_universe_service import MoexIndexUniverseService


class FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class MoexIndexUniverseServiceTests(unittest.TestCase):
    def test_extracts_tickers_from_standard_iss_table(self):
        payload = {
            "analytics": {
                "columns": ["id", "name", "ticker", "weight"],
                "data": [
                    [1, "Sber", "SBER", 13.2],
                    [2, "Lukoil", "LKOH", 15.3],
                    [3, "Novatek", "NVTK", 4.1],
                ],
            }
        }
        self.assertEqual(
            MoexIndexUniverseService._extract_tickers(payload),
            {"SBER", "LKOH", "NVTK"},
        )

    def test_filter_mappings_keeps_only_current_imoex_constituents(self):
        service = MoexIndexUniverseService(
            request_get=lambda *args, **kwargs: FakeResponse({})
        )
        service._cache = {"SBER", "LKOH"}
        service._cache_at = __import__("time").monotonic()

        mappings = [
            {"spot_ticker": "SBER", "futures_ticker": "SRU6", "futures_class_code": "TQBR"},
            {"spot_ticker": "LKOH", "futures_ticker": "LKU6", "futures_class_code": "TQBR"},
            {"spot_ticker": "ASTR", "futures_ticker": "ASU6", "futures_class_code": "TQBR"},
            {"spot_ticker": "IMOEX2", "futures_ticker": "MXU6", "futures_class_code": "SPBFUT"},
        ]

        result = service.filter_mappings(mappings)
        self.assertEqual(
            [item["spot_ticker"] for item in result],
            ["SBER", "LKOH"],
        )
        self.assertTrue(all(item["spot_universe"] == "IMOEX" for item in result))

    def test_refresh_failure_keeps_last_successful_snapshot(self):
        def failing_get(*args, **kwargs):
            raise TimeoutError("temporary ISS timeout")

        service = MoexIndexUniverseService(request_get=failing_get)
        service._cache = {"SBER", "GAZP"}
        service._cache_at = 0.0

        self.assertEqual(service.load(force=True), {"SBER", "GAZP"})


if __name__ == "__main__":
    unittest.main()
