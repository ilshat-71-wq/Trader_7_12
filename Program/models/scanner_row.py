from dataclasses import dataclass, field



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
    # Signal Engine
    # ----------------------------

    trade_score: int = 0


    direction: str = ""


    confidence: str = ""


    reasons: list = field(
        default_factory=list
    )


    signal: str = ""

    # ----------------------------
    # Instrument
    # ----------------------------

    lot_size: int = 1

# ----------------------------
# Instrument
# ----------------------------


