"""Select the most tradable futures contract for each SPOT candidate."""

from collections import defaultdict
from datetime import date
import math


class FuturesContractSelectorService:
    """Choose one live futures contract using expiry, spread and liquidity."""

    VERSION = "1.0"
    ORDER_BOOK_DEPTH = 10
    MIN_DAYS_TO_EXPIRY = 3
    LOOKBACK_TRADES_MINUTES = 30

    def __init__(self, api=None):
        self.api = api

    @staticmethod
    def _float(value, default=0.0):
        try:
            number = float(value)
            if math.isfinite(number):
                return number
        except (TypeError, ValueError):
            pass
        return default

    @classmethod
    def _expiry_days(cls, item, today=None):
        today = today or date.today()
        value = item.get("futures_expiry")
        try:
            expiry = value if isinstance(value, date) else date.fromisoformat(str(value)[:10])
        except (TypeError, ValueError):
            return None
        return (expiry - today).days

    @classmethod
    def _quote_map(cls, records):
        result = {}
        for record in records or []:
            if not isinstance(record, dict):
                continue
            key = (
                str(record.get("ticker") or "").strip().upper(),
                str(record.get("classCode") or "").strip(),
            )
            if key[0] and key[1]:
                result[key] = record
        return result

    @classmethod
    def _quote_values(cls, quote):
        if not isinstance(quote, dict):
            return None, None, None
        bid = cls._float(quote.get("bid"), 0.0)
        ask = cls._float(quote.get("offer", quote.get("ask")), 0.0)
        last = cls._float(quote.get("last", quote.get("lastPrice")), 0.0)
        if bid <= 0 or ask <= 0:
            return None, None, last if last > 0 else None
        return bid, ask, last if last > 0 else (bid + ask) / 2.0

    @classmethod
    def _order_book_metrics(cls, book):
        if not isinstance(book, dict):
            return None
        bids = book.get("bids") or []
        asks = book.get("asks") or []
        if not bids or not asks:
            return None

        bid = cls._float(bids[0].get("price"), 0.0)
        ask = cls._float(asks[0].get("price"), 0.0)
        if bid <= 0 or ask <= 0:
            return None

        bid_depth = sum(
            cls._float(level.get("price")) * cls._float(level.get("quantity"))
            for level in bids[: cls.ORDER_BOOK_DEPTH]
            if isinstance(level, dict)
        )
        ask_depth = sum(
            cls._float(level.get("price")) * cls._float(level.get("quantity"))
            for level in asks[: cls.ORDER_BOOK_DEPTH]
            if isinstance(level, dict)
        )
        mid = (bid + ask) / 2.0
        spread_percent = ((ask - bid) / mid * 100.0) if mid > 0 else None
        return {
            "bid": bid,
            "ask": ask,
            "spread_percent": spread_percent,
            "depth_notional": bid_depth + ask_depth,
            "bid_depth_notional": bid_depth,
            "ask_depth_notional": ask_depth,
        }

    @classmethod
    def _trade_turnover(cls, trades):
        turnover = 0.0
        count = 0
        for trade in trades or []:
            if not isinstance(trade, dict):
                continue
            price = cls._float(trade.get("price"), 0.0)
            quantity = cls._float(trade.get("quantity"), 0.0)
            if price <= 0:
                continue
            if quantity > 0:
                turnover += price * quantity
                count += 1
                continue
            volume = cls._float(trade.get("volume"), 0.0)
            if volume > 0:
                turnover += price * volume
                count += 1
        return turnover, count

    @staticmethod
    def _log_score(value, maximum):
        if value <= 0 or maximum <= 0:
            return 0.0
        return min(100.0, max(0.0, math.log1p(value) / math.log1p(maximum) * 100.0))

    @classmethod
    def _score_candidates(cls, rows):
        max_turnover = max((row["turnover_30m"] for row in rows), default=0.0)
        max_depth = max((row["depth_notional"] for row in rows), default=0.0)
        min_spread = min((row["spread_percent"] for row in rows if row["spread_percent"] is not None), default=None)
        max_days = max((row["days_to_expiry"] for row in rows), default=0)

        for row in rows:
            liquidity = (
                0.65 * cls._log_score(row["turnover_30m"], max_turnover)
                + 0.35 * cls._log_score(row["depth_notional"], max_depth)
            )

            spread = row["spread_percent"]
            if spread is None or min_spread is None:
                spread_score = 0.0
            elif spread <= 0:
                spread_score = 100.0
            else:
                spread_score = max(0.0, min(100.0, (min_spread / spread) * 100.0))

            expiry_score = 100.0
            if max_days > 0:
                expiry_score = max(0.0, min(100.0, 100.0 - ((row["days_to_expiry"] - min(row["days_to_expiry"] for row in rows)) / max_days) * 100.0))

            row["liquidity_score"] = round(liquidity, 2)
            row["spread_score"] = round(spread_score, 2)
            row["expiry_score"] = round(expiry_score, 2)
            row["selection_score"] = round(
                liquidity * 0.50 + spread_score * 0.30 + expiry_score * 0.20,
                2,
            )

    def select(self, mappings):
        """Return one eligible contract per SPOT mapping group."""
        if not isinstance(mappings, list) or not mappings or self.api is None:
            return []

        grouped = defaultdict(list)
        today = date.today()
        for mapping in mappings:
            if not isinstance(mapping, dict):
                continue
            ticker = str(mapping.get("futures_ticker") or "").strip().upper()
            class_code = str(mapping.get("futures_class_code") or "").strip()
            spot = str(mapping.get("spot_ticker") or "").strip().upper()
            if not ticker or not class_code or not spot:
                continue
            days = self._expiry_days(mapping, today=today)
            if days is None or days <= self.MIN_DAYS_TO_EXPIRY:
                continue
            item = dict(mapping)
            item["days_to_expiry"] = days
            grouped[spot].append(item)

        if not grouped:
            return []

        candidates = []
        for rows in grouped.values():
            rows.sort(key=lambda item: (item["days_to_expiry"], str(item.get("futures_ticker") or "")))
            candidates.extend(rows[:2])

        instruments = [
            {"ticker": item["futures_ticker"], "classCode": item["futures_class_code"]}
            for item in candidates
        ]

        try:
            quote_payload = self.api.get_quotes(instruments)
            quote_records = quote_payload.get("records", []) if isinstance(quote_payload, dict) else []
        except Exception:
            quote_records = []
        quotes = self._quote_map(quote_records)

        selected = []
        for spot, rows in grouped.items():
            rows = rows[:2]
            metrics = []
            for item in rows:
                key = (item["futures_ticker"], item["futures_class_code"])
                bid, ask, last = self._quote_values(quotes.get(key))
                if bid is None or ask is None:
                    continue
                try:
                    book = self.api.get_order_book(item["futures_ticker"], item["futures_class_code"])
                except Exception:
                    book = {}
                book_metrics = self._order_book_metrics(book)
                if book_metrics is None:
                    continue

                try:
                    trade_payload = self.api.get_last_trades(item["futures_ticker"], item["futures_class_code"])
                    trade_records = trade_payload.get("records", []) if isinstance(trade_payload, dict) else []
                except Exception:
                    trade_records = []
                turnover, trade_count = self._trade_turnover(trade_records)

                row = dict(item)
                row.update(book_metrics)
                row["last"] = last
                row["turnover_30m"] = round(turnover, 2)
                row["trade_count_30m"] = trade_count
                metrics.append(row)

            if not metrics:
                continue

            self._score_candidates(metrics)
            metrics.sort(key=lambda row: (
                row["selection_score"],
                row["liquidity_score"],
                row["spread_score"],
                -row["days_to_expiry"],
                row["futures_ticker"],
            ), reverse=True)
            best = metrics[0]
            best["futures_selection_version"] = self.VERSION
            best["futures_selection_reason"] = "expiry + 30m turnover + order-book depth + bid/ask spread"
            best["futures_selection_candidates"] = len(metrics)
            selected.append(best)

        return selected
