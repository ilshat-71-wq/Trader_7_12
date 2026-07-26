from dataclasses import dataclass


@dataclass
class ScannerRow:
    ticker: str
    short_name: str
    sector: str
    short_allowed: bool
    margin_allowed: bool
    market_cap: float