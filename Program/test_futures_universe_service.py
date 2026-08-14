from datetime import date

from services.futures_universe_service import FuturesUniverseService


class FakeAPI:
    def __init__(self, instruments):
        self.instruments = instruments

    def authorize(self):
        return True

    def get_instruments(self, instrument_type):
        assert instrument_type == "FUTURES"
        return self.instruments


def test_dynamic_universe_filters_and_deduplicates():
    service = FuturesUniverseService(
        FakeAPI(
            [
                {
                    "ticker": "SRU6",
                    "shortName": "SBER futures",
                    "boards": [{"classCode": "SPBFUT"}],
                },
                {
                    "ticker": "SRU6",
                    "shortName": "SBER futures duplicate",
                    "boards": [{"classCode": "SPBFUT"}],
                },
                {
                    "ticker": "BAD",
                    "shortName": "unknown",
                    "boards": [{"classCode": "SPBFUT"}],
                },
                {
                    "ticker": "OLDU5",
                    "shortName": "expired",
                    "boards": [{"classCode": "SPBFUT"}],
                },
                {
                    "ticker": "PERPU6",
                    "shortName": "PERPETUAL contract",
                    "boards": [{"classCode": "SPBFUT"}],
                },
            ]
        )
    )

    result = service.load()

    assert [item["ticker"] for item in result] == ["SRU6"]
    assert result[0]["classCode"] == "SPBFUT"
    assert result[0]["expiry"] >= date.today().isoformat()


def test_explicit_expiry_metadata_is_supported():
    service = FuturesUniverseService(
        FakeAPI(
            [
                {
                    "ticker": "CUSTOM1",
                    "shortName": "custom future",
                    "expirationDate": "2099-12-20T00:00:00Z",
                    "boards": [{"classCode": "SPBFUT"}],
                }
            ]
        )
    )

    result = service.load()

    assert len(result) == 1
    assert result[0]["expiry"] == "2099-12-20"
