"""Offline tests for Stage 5 SetupEngine."""

import unittest

from services.setup_engine import SetupEngine


def candle(high, low, close):
    return {"high": high, "low": low, "close": close}


class SetupEngineTests(unittest.TestCase):
    def test_pullback_long(self):
        candles = [
            candle(100.0, 99.8, 100.0),
            candle(100.5, 100.1, 100.3),
            candle(100.45, 100.20, 100.4),
            candle(100.7, 100.35, 100.6),
        ]
        result = SetupEngine._pullback(candles, "LONG")
        self.assertEqual(result["setup"], "PULLBACK")
        self.assertEqual(result["setup_state"], "READY")

    def test_rebound_long(self):
        candles = [
            candle(100.2, 99.0, 100.0),
            candle(99.6, 98.9, 99.2),
            candle(100.0, 99.1, 99.8),
        ]
        result = SetupEngine._rebound(candles, "LONG")
        self.assertEqual(result["setup"], "REBOUND")
        self.assertEqual(result["setup_state"], "READY")

    def test_breakout_short(self):
        candles = [
            candle(100.0, 99.0, 99.5),
            candle(100.1, 99.1, 99.6),
            candle(100.0, 99.2, 99.7),
            candle(99.0, 98.5, 98.7),
        ]
        result = SetupEngine._breakout(candles, "SHORT")
        self.assertEqual(result["setup"], "BREAKOUT")
        self.assertEqual(result["setup_state"], "READY")

    def test_retest_long(self):
        candles = [
            candle(100.0, 99.0, 99.5),
            candle(100.1, 99.1, 99.6),
            candle(100.0, 99.2, 99.7),
            candle(101.5, 99.9, 101.3),
            candle(101.2, 100.9, 101.0),
            candle(101.7, 101.0, 101.6),
        ]
        result = SetupEngine._retest(candles, "LONG")
        self.assertEqual(result["setup"], "RETEST")
        self.assertEqual(result["setup_state"], "READY")
        self.assertEqual(result["confirmation_index"], 5)

    def test_analyze_returns_earliest_ready_setup(self):
        candles = [
            candle(100.0, 99.0, 99.5),
            candle(100.1, 99.1, 99.6),
            candle(100.0, 99.2, 99.7),
            candle(100.5, 99.8, 100.4),
        ]
        result = SetupEngine.analyze(candles, "LONG")
        self.assertEqual(result["setup_direction"], "LONG")
        self.assertIn(result["setup"], {"PULLBACK", "BREAKOUT", "REBOUND", "NONE"})
        self.assertEqual(result["candle_count"], 4)
        self.assertEqual(len(result["candidates"]), 4)

    def test_invalid_direction(self):
        with self.assertRaises(ValueError):
            SetupEngine.analyze([], "SIDEWAYS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
