"""Trader_7_12 Pro — real money-flow analysis.

The legacy calculate() API is preserved. Snapshot analysis uses only real BCS
last trades and current order-book data; it never invents price, volume or a
participant identity.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from math import log1p


class MoneyFlowService:
    VERSION = "1.0.0"
    WINDOW_MINUTES = 30
    MAX_WORKERS = 5
    MIN_TRADES = 5

    def calculate(self, money_volume=0, average_money_volume=0):
        try:
            money_volume = float(money_volume or 0)
        except (TypeError, ValueError):
            money_volume = 0.0
        try:
            average_money_volume = float(average_money_volume or 0)
        except (TypeError, ValueError):
            average_money_volume = 0.0
        money_ratio = money_volume / average_money_volume if average_money_volume > 0 else 0.0
        if money_ratio >= 5: score = 100
        elif money_ratio >= 3: score = 90
        elif money_ratio >= 2: score = 80
        elif money_ratio >= 1.5: score = 65
        elif money_ratio >= 1: score = 50
        elif money_ratio >= 0.75: score = 30
        else: score = 15
        if money_ratio >= 3: state = "EXTREME"
        elif money_ratio >= 2: state = "STRONG"
        elif money_ratio >= 1.5: state = "ELEVATED"
        elif money_ratio >= 1: state = "NORMAL"
        elif money_ratio >= 0.75: state = "WEAK"
        else: state = "VERY_WEAK"
        return {"money_volume": round(money_volume, 2), "average_money_volume": round(average_money_volume, 2), "money_ratio": round(money_ratio, 2), "money_activity_score": score, "money_activity_state": state}

    @staticmethod
    def _float(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def _trade_value(cls, trade):
        value = cls._float(trade.get("volume"))
        if value > 0:
            return value
        return max(0.0, cls._float(trade.get("price")) * cls._float(trade.get("quantity"), cls._float(trade.get("tradeQuantity"))))

    @staticmethod
    def _percentile(values, fraction=0.90):
        values = sorted(v for v in values if v > 0)
        if not values:
            return 0.0
        return values[min(len(values) - 1, int(round((len(values) - 1) * fraction)))]

    @classmethod
    def analyze_snapshot(cls, ticker, class_code, trades_data, book):
        records = trades_data.get("records", []) if isinstance(trades_data, dict) else []
        trades = []
        for trade in records if isinstance(records, list) else []:
            if not isinstance(trade, dict):
                continue
            side = str(trade.get("side") or "").upper()
            price = cls._float(trade.get("price"))
            value = cls._trade_value(trade)
            if side in {"BUY", "SELL"} and price > 0 and value > 0:
                trades.append((side, price, value))

        if not trades:
            return {"money_flow_status": "NO_DATA", "money_flow_signal": "NO_DATA", "money_flow_confidence": "LOW", "money_flow_source": "BCS_LAST_TRADES_30M_PLUS_CURRENT_ORDER_BOOK"}

        total = sum(v for _, _, v in trades)
        buy = sum(v for s, _, v in trades if s == "BUY")
        sell = sum(v for s, _, v in trades if s == "SELL")
        delta = buy - sell
        delta_pct = delta / total * 100.0 if total else 0.0
        first_price = trades[0][1]
        latest_price = trades[-1][1]
        price_change_pct = (latest_price / first_price - 1.0) * 100.0 if first_price else 0.0
        vwap = sum(p * v for _, p, v in trades) / total if total else None
        dominant = "BUY" if buy > sell else "SELL" if sell > buy else "NEUTRAL"
        dominant_trades = [(p, v) for s, p, v in trades if s == dominant]
        zone_low = min((p for p, _ in dominant_trades), default=None)
        zone_high = max((p for p, _ in dominant_trades), default=None)
        zone_total = sum(v for _, v in dominant_trades)
        zone_vwap = sum(p * v for p, v in dominant_trades) / zone_total if zone_total else None

        threshold = cls._percentile([v for _, _, v in trades])
        large = [(s, p, v) for s, p, v in trades if threshold and v >= threshold]
        large_buy = sum(v for s, _, v in large if s == "BUY")
        large_sell = sum(v for s, _, v in large if s == "SELL")

        bid = cls._float(book.get("bidVolume")) if isinstance(book, dict) else 0.0
        ask = cls._float(book.get("askVolume")) if isinstance(book, dict) else 0.0
        if not bid and isinstance(book, dict):
            bid = sum(cls._float(x.get("quantity")) for x in book.get("bids", []) if isinstance(x, dict))
        if not ask and isinstance(book, dict):
            ask = sum(cls._float(x.get("quantity")) for x in book.get("asks", []) if isinstance(x, dict))
        book_total = bid + ask
        book_imbalance = (bid - ask) / book_total * 100.0 if book_total else 0.0
        flow_sign = 1 if dominant == "BUY" else -1 if dominant == "SELL" else 0
        book_sign = 1 if book_imbalance > 10 else -1 if book_imbalance < -10 else 0
        aligned = flow_sign != 0 and flow_sign == book_sign

        if len(trades) < cls.MIN_TRADES or abs(delta_pct) < 12:
            signal = "BALANCED"
        elif dominant == "BUY":
            signal = "BUY_ABSORPTION" if delta_pct >= 20 and price_change_pct <= 0.10 else "ACCUMULATION" if latest_price >= (vwap or latest_price) else "BUYER_ACTIVE"
        else:
            signal = "SELL_ABSORPTION" if delta_pct <= -20 and price_change_pct >= -0.10 else "DISTRIBUTION" if latest_price <= (vwap or latest_price) else "SELLER_ACTIVE"

        score = min(100.0, abs(delta_pct) * 0.55 + min(30.0, log1p(len(large)) * 10.0) + (15.0 if aligned else 0.0))
        confidence = "HIGH" if score >= 70 and len(trades) >= 10 else "MEDIUM" if score >= 40 and len(trades) >= cls.MIN_TRADES else "LOW"
        return {
            "money_flow_status": "AVAILABLE",
            "money_flow_window_minutes": cls.WINDOW_MINUTES,
            "money_flow_total": round(total, 2),
            "money_flow_buy": round(buy, 2),
            "money_flow_sell": round(sell, 2),
            "money_flow_delta": round(delta, 2),
            "money_flow_delta_pct": round(delta_pct, 2),
            "money_flow_trade_count": len(trades),
            "money_flow_large_trade_count": len(large),
            "money_flow_large_buy": round(large_buy, 2),
            "money_flow_large_sell": round(large_sell, 2),
            "money_flow_large_trade_threshold": round(threshold, 2),
            "money_flow_latest_price": latest_price,
            "money_flow_price_change_pct": round(price_change_pct, 4),
            "money_flow_vwap": round(vwap, 8) if vwap is not None else None,
            "money_flow_zone_low": zone_low,
            "money_flow_zone_high": zone_high,
            "money_flow_zone_vwap": round(zone_vwap, 8) if zone_vwap is not None else None,
            "money_flow_signal": signal,
            "money_flow_book_bid": round(bid, 2),
            "money_flow_book_ask": round(ask, 2),
            "money_flow_book_imbalance_pct": round(book_imbalance, 2),
            "money_flow_book_aligned": aligned,
            "money_flow_score": round(score, 1),
            "money_flow_confidence": confidence,
            "money_flow_position_claim": "PROBABLE_FLOW_ZONE_ONLY",
            "money_flow_source": "BCS_LAST_TRADES_30M_PLUS_CURRENT_ORDER_BOOK",
            "money_flow_observed_at": datetime.now(timezone.utc).isoformat(),
        }

    def _one(self, item, api):
        ticker = str(item.get("underlying_bcs_ticker") or item.get("underlying_ticker") or "").upper()
        class_code = str(item.get("underlying_class_code") or "").upper()
        if not ticker or not class_code:
            return dict(item, money_flow_status="NO_CLASS_CODE", money_flow_signal="NO_DATA", money_flow_confidence="LOW")
        try:
            trades = api.get_last_trades(ticker, class_code)
        except Exception:
            trades = {"records": []}
        try:
            book = api.get_order_book(ticker, class_code)
        except Exception:
            book = {}
        result = dict(item)
        result.update(self.analyze_snapshot(ticker, class_code, trades, book))
        return result

    def analyze(self, results, api=None):
        api = api or getattr(self, "api", None)
        if not results or api is None:
            return results or []
        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            futures = [executor.submit(self._one, item, api) for item in results]
            enriched = [future.result() for future in as_completed(futures)]
        enriched.sort(key=lambda row: float(row.get("money_flow_score") or 0.0), reverse=True)
        rank = 0
        for item in enriched:
            if item.get("money_flow_status") == "AVAILABLE":
                rank += 1
                item["money_flow_rank"] = rank
            else:
                item["money_flow_rank"] = None
        return enriched
