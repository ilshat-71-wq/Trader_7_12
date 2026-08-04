from dataclasses import dataclass



@dataclass
class ScannerRow:


    ticker: str


    last: float


    change: float


    volume: float


    money_volume: float


    rating: int = 0


    # ----------------------------
    # Volume Price Analyzer
    # ----------------------------

    volume_ratio: float = 0


    volume_score: int = 0


    # ----------------------------
    # Momentum
    # ----------------------------

    momentum_score: int = 0


    range_position: float = 0


    # ----------------------------
    # Trading signal
    # ----------------------------

    signal: str = ""