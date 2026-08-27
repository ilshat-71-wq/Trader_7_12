from services.spot_universe_service import SpotUniverseService
from services.historical_universe_replay_service import HistoricalUniverseReplayService


class _FakeSpotApi:
    access_token = "token"

    def authorize(self):
        return True

    def get_instruments(self, instrument_type):
        return {
            "STOCK": [{"ticker": "SBER", "boards": [{"exchange": "MOEX", "classCode": "TQBR"}]}],
            "CURRENCY": [{"ticker": "USDRUB", "classCode": "CETS"}],
            "GOODS": [{"ticker": "LCROIL1026NY", "classCode": "FEG"}],
            "COMMODITY": [], "COMMODITIES": [], "METALS": [], "INDICES": [],
        }.get(instrument_type, [])


class _FailingFuturesMapping:
    def load(self):
        raise AssertionError("futures mapping must not be consulted for SPOT universe")


def test_spot_universe_is_loaded_without_futures_dependency():
    service = SpotUniverseService(api=_FakeSpotApi())
    spots = service.load()
    keys = {(item["spot_ticker"], item["spot_class_code"]) for item in spots}
    assert ("SBER", "TQBR") in keys
    assert ("USDRUB", "CETS") in keys
    assert ("LCROIL1026NY", "FEG") in keys


def test_historical_spot_universe_does_not_call_futures_mapping():
    service = HistoricalUniverseReplayService(
        mapping_service=_FailingFuturesMapping(),
        spot_universe_service=SpotUniverseService(api=_FakeSpotApi()),
    )
    spots = service.load_spot_universe()
    assert {item["spot_ticker"] for item in spots} == {"LCROIL1026NY", "SBER", "USDRUB"}
