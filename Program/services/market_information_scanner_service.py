"""Canonical read-only market-information scanner facade.

This facade keeps the existing data pipeline while exposing a strictly
informational vocabulary to the application: market leaders, market laggards
and high current attention. It never presents a trading decision.
"""

from services.market_attention_scanner_service import MarketAttentionScannerService as _PipelineScanner


class MarketInformationScannerService(_PipelineScanner):
    """Read-only information facade over the production market scanner."""

    VERSION = "2.3.1"

    def scan(self, limit=3):
        rows = super().scan(limit=limit)
        translated = []
        role_map = {
            "LONG_CANDIDATE": "MARKET_LEADER",
            "SHORT_CANDIDATE": "MARKET_LAGGARD",
            "ATTENTION_WATCH": "ATTENTION_WATCH",
        }
        for row in rows:
            item = dict(row)
            item["selection_role"] = role_map.get(item.get("selection_role"), item.get("selection_role"))
            direction = str(item.get("direction") or "NEUTRAL").upper()
            item["market_state"] = {"LONG": "STRONG", "SHORT": "WEAK"}.get(direction, "NEUTRAL")
            item.pop("direction", None)
            translated.append(item)
        diagnostics = dict(getattr(self, "_last_scan_diagnostics", {}) or {})
        diagnostics["information_model"] = "MARKET_FACTS_ONLY"
        diagnostics["decision_policy"] = "NO_TRADE_DECISION"
        diagnostics["leader_role"] = "MARKET_LEADER"
        diagnostics["laggard_role"] = "MARKET_LAGGARD"
        self._last_scan_diagnostics = diagnostics
        return translated
