"""
Trader_7_12 Pro

Futures Confirmation Service

Stage 4 of the Spot-first architecture.

Purpose:
- verify that the selected futures contract supports the SPOT idea;
- measure current futures activity and money volume;
- never create or reverse the SPOT direction;
- return CONFIRMED / BLOCKED / NO_DATA for the next execution stage.

This service is intentionally small. It does not calculate the SPOT idea,
does not choose a different direction, and does not place orders.
"""


class FuturesConfirmationService:
    """Confirm whether a futures contract is suitable for a SPOT idea."""

    VERSION = "0.1"
    MIN_TRADES = 20
    MIN_MONEY_VOLUME = 1_000_000.0

    def __init__(self, api=None):
        self.api = api

    @staticmethod
    def _float(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def _direction_from_trades(cls, trades):
        if not trades:
            return "NONE"

        first_price = cls._float(trades[0].get("price"))
        last_price = cls._float(trades[-1].get("price"))

        if first_price <= 0 or last_price <= 0:
            return "NONE"
        if last_price > first_price:
            return "LONG"
        if last_price < first_price:
            return "SHORT"
        return "FLAT"

    @classmethod
    def analyze_trades(cls, trades, spot_direction):
        """Analyze supplied futures trades without network access."""
        if not isinstance(trades, list) or not trades:
            return {
                "version": cls.VERSION,
                "status": "NO_DATA",
                "confirmation": "NO_DATA",
                "direction": "NONE",
                "spot_direction": str(spot_direction or "NONE").upper(),
                "trade_count": 0,
                "money_volume": 0.0,
                "price_change_percent": 0.0,
                "score": 0,
                "reason": "No futures trades available",
            }

        valid = []
        money_volume = 0.0

        for trade in trades:
            if not isinstance(trade, dict):
                continue

            price = cls._float(trade.get("price"))
            volume = cls._float(
                trade.get("volume", trade.get("quantity"))
            )

            if price <= 0 or volume <= 0:
                continue

            valid.append(trade)
            money_volume += price * volume

        if not valid:
            return {
                "version": cls.VERSION,
                "status": "NO_DATA",
                "confirmation": "NO_DATA",
                "direction": "NONE",
                "spot_direction": str(spot_direction or "NONE").upper(),
                "trade_count": 0,
                "money_volume": 0.0,
                "price_change_percent": 0.0,
                "score": 0,
                "reason": "No valid futures trades available",
            }

        first_price = cls._float(valid[0].get("price"))
        last_price = cls._float(valid[-1].get("price"))
        direction = cls._direction_from_trades(valid)

        if first_price > 0:
            price_change_percent = (
                (last_price - first_price) / first_price * 100
            )
        else:
            price_change_percent = 0.0

        expected = str(spot_direction or "NONE").upper()
        if expected not in {"LONG", "SHORT"}:
            return {
                "version": cls.VERSION,
                "status": "BLOCKED",
                "confirmation": "BLOCKED",
                "direction": direction,
                "spot_direction": expected,
                "trade_count": len(valid),
                "money_volume": round(money_volume, 2),
                "price_change_percent": round(price_change_percent, 4),
                "score": 0,
                "reason": "SPOT direction is not tradable",
            }

        if direction not in {"LONG", "SHORT"}:
            return {
                "version": cls.VERSION,
                "status": "BLOCKED",
                "confirmation": "BLOCKED",
                "direction": direction,
                "spot_direction": expected,
                "trade_count": len(valid),
                "money_volume": round(money_volume, 2),
                "price_change_percent": round(price_change_percent, 4),
                "score": 0,
                "reason": "Futures direction is not directional",
            }

        if direction != expected:
            return {
                "version": cls.VERSION,
                "status": "BLOCKED",
                "confirmation": "BLOCKED",
                "direction": direction,
                "spot_direction": expected,
                "trade_count": len(valid),
                "money_volume": round(money_volume, 2),
                "price_change_percent": round(price_change_percent, 4),
                "score": 0,
                "reason": "Futures direction conflicts with SPOT idea",
            }

        if len(valid) < cls.MIN_TRADES:
            return {
                "version": cls.VERSION,
                "status": "BLOCKED",
                "confirmation": "BLOCKED",
                "direction": direction,
                "spot_direction": expected,
                "trade_count": len(valid),
                "money_volume": round(money_volume, 2),
                "price_change_percent": round(price_change_percent, 4),
                "score": 0,
                "reason": "Insufficient futures trade activity",
            }

        if money_volume < cls.MIN_MONEY_VOLUME:
            return {
                "version": cls.VERSION,
                "status": "BLOCKED",
                "confirmation": "BLOCKED",
                "direction": direction,
                "spot_direction": expected,
                "trade_count": len(valid),
                "money_volume": round(money_volume, 2),
                "price_change_percent": round(price_change_percent, 4),
                "score": 0,
                "reason": "Insufficient futures money volume",
            }

        score = 60
        if len(valid) >= 50:
            score += 15
        elif len(valid) >= 30:
            score += 10

        if abs(price_change_percent) >= 1:
            score += 15
        elif abs(price_change_percent) >= 0.5:
            score += 10
        else:
            score += 5

        if money_volume >= 100_000_000:
            score += 10
        elif money_volume >= 10_000_000:
            score += 5

        return {
            "version": cls.VERSION,
            "status": "OK",
            "confirmation": "CONFIRMED",
            "direction": direction,
            "spot_direction": expected,
            "trade_count": len(valid),
            "money_volume": round(money_volume, 2),
            "price_change_percent": round(price_change_percent, 4),
            "score": min(score, 100),
            "reason": "Futures activity confirms the SPOT direction",
        }

    def analyze(self, futures_ticker, futures_class_code, spot_direction):
        """Load current futures trades and confirm the supplied SPOT idea."""
        if self.api is None:
            raise RuntimeError("BCS API is not configured")

        trades_result = self.api.get_last_trades(
            futures_ticker,
            futures_class_code
        )
        trades = (
            trades_result.get("records", [])
            if isinstance(trades_result, dict)
            else []
        )

        result = self.analyze_trades(trades, spot_direction)
        result.update({
            "futures_ticker": futures_ticker,
            "futures_class_code": futures_class_code,
        })
        return result
