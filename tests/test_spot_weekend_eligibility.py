from services.spot_universe_service import SpotUniverseService


class FakeAPI:
    access_token = "test"

    def authorize(self):
        return True

    def get_instruments(self, instrument_type):
        if instrument_type != "STOCK":
            return []
        return [
            {
                "ticker": "WEEK",
                "classCode": "TQBR",
                "WEEKENDSESSION": "Y",
            },
            {
                "ticker": "NOPE",
                "classCode": "TQBR",
                "WEEKENDSESSION": "N",
            },
            {
                "ticker": "BOARD",
                "boards": [
                    {
                        "exchange": "MOEX",
                        "classCode": "TQBR",
                        "weekendSession": "Y",
                    }
                ],
            },
            {
                "ticker": "UNKNOWN",
                "classCode": "TQBR",
            },
        ]


def test_weekend_flag_reads_security_and_board_metadata():
    assert SpotUniverseService._weekend_flag({"WEEKENDSESSION": "Y"}) is True
    assert SpotUniverseService._weekend_flag({"WEEKENDSESSION": "N"}) is False
    assert SpotUniverseService._weekend_flag(
        {"boards": [{"weekendSession": "Y"}]}
    ) is True
    assert SpotUniverseService._weekend_flag({"WEEKENDSESSION": "unknown"}) is None


def test_weekend_universe_requires_explicit_real_eligibility():
    service = SpotUniverseService(api=FakeAPI())
    rows = service.load(weekend_session=True)
    assert {(row["spot_ticker"], row["spot_class_code"]) for row in rows} == {
        ("WEEK", "TQBR"),
        ("BOARD", "TQBR"),
    }


def test_regular_universe_does_not_apply_weekend_eligibility_filter():
    service = SpotUniverseService(api=FakeAPI())
    rows = service.load(weekend_session=False)
    tickers = {row["spot_ticker"] for row in rows}
    assert tickers == {"WEEK", "NOPE", "BOARD", "UNKNOWN"}
