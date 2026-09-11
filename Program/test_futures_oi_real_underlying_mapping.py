import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "Program"
if str(PROGRAM) not in sys.path:
    sys.path.insert(0, str(PROGRAM))

from api.bcs_api import BCSAPI


def test_record_aliases_include_real_bcs_base_asset():
    record = {
        "ticker": "CNYRUB_TOM",
        "baseAssetTicker": "CNYRUB",
        "classCode": "CETS",
    }

    aliases = BCSAPI._record_aliases(record)

    assert "CNYRUB" in aliases
    assert "CNYRUBTOM" not in aliases
    assert "CNYRUBTOM" not in {BCSAPI._instrument_lookup_key(x) for x in ["CNYRUB_TOM"]}


def test_record_aliases_include_gold_spot():
    record = {
        "ticker": "GLDRUB_TOM",
        "baseAssetTicker": "GLDRUB",
        "classCode": "CETS",
    }

    aliases = BCSAPI._record_aliases(record)

    assert "GLDRUB" in aliases


def test_record_aliases_use_underlying_metadata_fields():
    record = {
        "ticker": "SOMETHING",
        "underlyingTicker": "SBER",
        "assetCode": "SBER",
        "classCode": "TQBR",
    }

    aliases = BCSAPI._record_aliases(record)

    assert "SBER" in aliases
