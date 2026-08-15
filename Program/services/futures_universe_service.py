"""
Trader_7_12 Pro

Futures Universe Service

Stage 1 of the Spot-first architecture.

Purpose:
- load all currently available MOEX futures from BCS;
- keep only real, dated futures contracts suitable for analysis;
- exclude expired / perpetual / technical contracts where they can be
  identified from the instrument metadata;
- do NOT choose a fixed list of instruments;
- do NOT perform Futures -> SPOT mapping here.

The service is intentionally limited to universe construction. Trading
logic belongs to later stages.
"""

from datetime import date, datetime

from api.bcs_api import BCSAPI


class FuturesUniverseService:
    """Build the current dynamic futures universe used by the project."""

    FUTURES_TYPE = "FUTURES"

    def __init__(self, api=None):
        self.api = api or BCSAPI()

    def load(self, authorize=True):
        """Return the current dynamic futures universe."""
        if authorize and not self.api.authorize():
            return []

        instruments = self.api.get_instruments(self.FUTURES_TYPE)

        if not isinstance(instruments, list):
            return []

        result = []
        seen = set()

        for item in instruments:
            normalized = self._normalize(item)

            if normalized is None:
                continue

            key = (
                normalized["ticker"],
                normalized["classCode"],
            )

            if key in seen:
                continue

            seen.add(key)
            result.append(normalized)

        result.sort(key=lambda item: item["ticker"])
        return result

    def _normalize(self, item):
        if not isinstance(item, dict):
            return None

        ticker = str(item.get("ticker") or "").strip().upper()
        if not ticker:
            return None

        name = str(
            item.get("shortName")
            or item.get("displayName")
            or ""
        ).strip()

        text = f"{ticker} {name} {item.get('displayName') or ''}".upper()

        if self._is_perpetual(item, text):
            return None

        expiry = self._extract_expiry(item, ticker)
        if expiry is None:
            return None

        if expiry < date.today():
            return None

        class_code = self._class_code(item)
        if not class_code:
            return None

        return {
            "asset": "FUTURES",
            "ticker": ticker,
            "classCode": class_code,
            "name": name,
            "displayName": str(item.get("displayName") or "").strip(),
            "shortName": str(item.get("shortName") or "").strip(),
            "expiry": expiry.isoformat(),
            "lotSize": item.get("lotSize", 1),
            # Preserve BCS underlying metadata exactly enough for Stage 2.
            "underlyingTicker": item.get("underlyingTicker"),
            "underlying_ticker": item.get("underlying_ticker"),
            "underlyingSecurityCode": item.get("underlyingSecurityCode"),
            "underlyingSecurity": item.get("underlyingSecurity"),
            "underlyingSecurityClassCode": item.get("underlyingSecurityClassCode"),
            "underlying_security_class_code": item.get("underlying_security_class_code"),
            "baseTicker": item.get("baseTicker"),
            "base_ticker": item.get("base_ticker"),
            "spotTicker": item.get("spotTicker"),
            "spot_ticker": item.get("spot_ticker"),
            "underlyingAsset": item.get("underlyingAsset"),
            "underlyingAssetTicker": item.get("underlyingAssetTicker"),
            # Canonical BCS Trade API futures-underlying fields.
            "baseAsset": item.get("baseAsset"),
            "baseAssetFuture": item.get("baseAssetFuture"),
            "baseAssetSecurity": item.get("baseAssetSecurity"),
            "baseAssetSecuritySecCode": item.get("baseAssetSecuritySecCode"),
            "baseAssetSecurityClassCode": item.get("baseAssetSecurityClassCode"),
            # Keep the raw class/board metadata available for future diagnostics.
            "boards": item.get("boards"),
        }

    @staticmethod
    def _class_code(item):
        boards = item.get("boards") or []

        if isinstance(boards, list):
            for board in boards:
                if not isinstance(board, dict):
                    continue
                class_code = str(board.get("classCode") or "").strip()
                if class_code:
                    return class_code

        return str(item.get("classCode") or "").strip()

    @staticmethod
    def _is_perpetual(item, text):
        for key in ("isPerpetual", "perpetual"):
            if item.get(key) is True:
                return True

        markers = (
            "PERPETUAL",
            "PERP",
            "БЕССРОЧ",
        )

        return any(marker in text for marker in markers)

    @classmethod
    def _extract_expiry(cls, item, ticker):
        for key in (
            "expirationDate",
            "expiryDate",
            "expiration",
            "expiry",
            "maturityDate",
        ):
            value = item.get(key)
            parsed = cls._parse_date(value)
            if parsed is not None:
                return parsed

        if len(ticker) < 2:
            return None

        months = {
            "F": 1,
            "G": 2,
            "H": 3,
            "J": 4,
            "K": 5,
            "M": 6,
            "N": 7,
            "Q": 8,
            "U": 9,
            "V": 10,
            "X": 11,
            "Z": 12,
        }

        month = months.get(ticker[-2])
        year_code = ticker[-1]

        if month is None or not year_code.isdigit():
            return None

        year = 2020 + int(year_code)
        return date(year, month, 1)

    @staticmethod
    def _parse_date(value):
        if not value:
            return None

        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        text = str(value).strip()
        if not text:
            return None

        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        try:
            return datetime.fromisoformat(text).date()
        except ValueError:
            pass

        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None
