import logging
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "Journal"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / "scanner.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("TraderScanner")