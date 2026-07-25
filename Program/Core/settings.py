from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

CACHE_DIR = BASE_DIR / "Cache"
DATABASE_DIR = BASE_DIR / "Database"
DATA_DIR = BASE_DIR / "Data"

CACHE_DIR.mkdir(exist_ok=True)
DATABASE_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

UPDATE_QUOTES_SEC = 2
UPDATE_SCANNER_SEC = 5
MARKET_OPEN = "07:00"
MARKET_CLOSE = "13:00"