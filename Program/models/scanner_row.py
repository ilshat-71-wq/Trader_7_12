from dataclasses import dataclass


@dataclass
class ScannerRow:

    ticker: str

    last: float

    change: float

    volume: float

    money_volume: float

    rating: int = 0