"""Canonical read-only market-information scanner facade.

This facade keeps the existing data pipeline while exposing the production
scanner's D1-first candidate roles to the application. It never presents a
trading execution decision.
"""

from services.market_attention_scanner_service import MarketAttentionScannerService as _PipelineScanner


class MarketInformationScannerService(_PipelineScanner):
    """Read-only information facade over the production market scanner."""

    VERSION = "2.6.0"

    def scan(self, limit=3):
        rows = super().scan(limit=limit)
        translated = []
        for row in rows:
            item = dict(row)
            direction = str(item.get("direction") or "NEUTRAL").upper()
            item["market_state"] = {"LONG": "STRONG", "SHORT": "WEAK"}.get(direction, "NEUTRAL")
            translated.append(item)
        diagnostics = dict(getattr(self, "_last_scan_diagnostics", {}) or {})
        diagnostics["information_model"] = "MARKET_FACTS_ONLY"
        diagnostics["decision_policy"] = "NO_TRADE_DECISION"
        self._last_scan_diagnostics = diagnostics
        return translated
