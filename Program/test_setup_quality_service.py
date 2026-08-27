"""Offline regression tests for canonical SPOT setup quality."""

import unittest

from services.setup_quality_service import SetupQualityService


class SetupQualityServiceTests(unittest.TestCase):
    def test_none_setup_has_zero_quality(self):
        result = SetupQualityService.score({"setup": "NONE"}, [])
        self.assertEqual(result["setup_quality_score"], 0.0)
        self.assertEqual(result["quality_components"], {})

    def test_quality_is_bounded_and_transparent(self):
        setup = {
            "setup": "BREAKOUT",
            "setup_direction": "LONG",
            "setup_index": 0,
            "confirmation_index": 0,
            "level": 100.0,
            "entry_trigger": 101.0,
        }
        candles = [{"open": 100.0, "high": 101.2, "low": 99.9, "close": 101.0}]
        result = SetupQualityService.score(setup, candles)
        self.assertGreaterEqual(result["setup_quality_score"], 0.0)
        self.assertLessEqual(result["setup_quality_score"], 100.0)
        self.assertEqual(set(result["quality_components"]), {"geometry", "candle", "rejection", "continuation"})
        self.assertEqual(result["quality_components"]["continuation"], 100.0)

    def test_unconfirmed_setup_is_not_treated_as_confirmed(self):
        setup = {
            "setup": "PULLBACK",
            "setup_direction": "SHORT",
            "setup_index": 0,
            "confirmation_index": None,
            "level": 100.0,
            "entry_trigger": 99.8,
        }
        candles = [{"open": 100.0, "high": 100.2, "low": 99.7, "close": 99.9}]
        result = SetupQualityService.score(setup, candles)
        self.assertEqual(result["quality_components"]["continuation"], 25.0)
        self.assertIn("continuation not yet confirmed", result["setup_quality_reasons"])

    def test_missing_ohlc_does_not_invent_candle_quality(self):
        setup = {
            "setup": "BREAKOUT",
            "setup_direction": "LONG",
            "setup_index": 0,
            "confirmation_index": 0,
            "level": 100.0,
            "entry_trigger": 100.5,
        }
        result = SetupQualityService.score(setup, [{}])
        self.assertEqual(result["quality_components"]["candle"], 0.0)
        self.assertEqual(result["quality_components"]["rejection"], 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
