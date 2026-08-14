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

    VERSION = "0.2"
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
    def _result(
        cls,
        status,
        confirmation,
        direction,
        spot_direction,
        trade_count,
        money_volume,
        price_change_percent,
        score,
        reason,
        last_price=0.0,
    ):
        return {
            "version": cls.VERSION,
            "status": status,
            "confirmation": confirmation,
            "direction": direction,
            "spot_direction": str(spot_direction or "NONE").upper(),
            "trade_count": trade_count,
            "money_volume": round(money_volume, 2),
            "price_change_percent": round(price_change_percent, 4),
            "last_price": round(last_price, 8),
            "score": score,
            "reason": reason,
        }

    @classmethod
    def analyze_trades(cls, trades, spot_direction):
        """Analyze supplied futures trades without network access."""
        expected = str(spot_direction or "NONE").upper()

        if not isinstance(trades, list) or not trades:
            return cls._result(
                "NO_DATA", "NO_DATA", "NONE", expected,
                0, 0.0, 0.0, 0,
                "No futures trades available",
            )

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
            return cls._result(
                "NO_DATA", "NO_DATA", "NONE", expected,
                0, 0.0, 0.0, 0,
                "No valid futures trades available",
            )

        first_price = cls._float(valid[0].get("price"))
        last_price = cls._float(valid[-1].get("price"))
        direction = cls._direction_from_trades(valid)

        if first_price > 0:
            price_change_percent = (
                (last_price - first_price) / first_price * 100
            )
        else:
            price_change_percent = 0.0

        if expected not in {"LONG", "SHORT"}:
            return cls._result(
                "BLOCKED", "BLOCKED", direction, expected,
                len(valid), money_volume, price_change_percent, 0,
                "SPOT direction is not tradable", last_price,
            )

        if direction not in {"LONG", "SHORT"}:
            return cls._result(
                "BLOCKED", "BLOCKED", direction, expected,
                len(valid), money_volume, price_change_percent, 0,
                "Futures direction is not directional", last_price,
            )

        if direction != expected:
            return cls._result(
                "BLOCKED", "BLOCKED", direction, expected,
                len(valid), money_volume, price_change_percent, 0,
                "Futures direction conflicts with SPOT idea", last_price,
            )

        if len(valid) < cls.MIN_TRADES:
            return cls._result(
                "BLOCKED", "BLOCKED", direction, expected,
                len(valid), money_volume, price_change_percent, 0,
                "Insufficient futures trade activity", last_price,
            )

        if money_volume < cls.MIN_MONEY_VOLUME:
            return cls._result(
                "BLOCKED", "BLOCKED", direction, expected,
                len(valid), money_volume, price_change_percent, 0,
                "Insufficient futures money volume", last_price,
            )

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

        return cls._result(
            "OK", "CONFIRMED", direction, expected,
            len(valid), money_volume, price_change_percent,
            min(score, 100),
            "Futures activity confirms the SPOT direction",
            last_price,
        )

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
