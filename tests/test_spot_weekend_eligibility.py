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
                # BCS metadata is not authoritative for weekend admission.
                "WEEKENDSESSION": "N",
            },
            {
                "ticker": "NOPE",
                "classCode": "TQBR",
                # A BCS flag alone must not admit this instrument.
                "WEEKENDSESSION": "Y",
            },
            {
                "ticker": "BOARD",
                "boards": [
                    {
                        "exchange": "MOEX",
                        "classCode": "TQBR",
                    }
                ],
            },
            {
                "ticker": "UNKNOWN",
                "classCode": "TQBR",
            },
        ]


def test_weekend_flag_parses_explicit_metadata_values():
    assert SpotUniverseService._weekend_flag({"WEEKENDSESSION": "Y"}) is True
    assert SpotUniverseService._weekend_flag({"WEEKENDSESSION": "N"}) is False
    assert SpotUniverseService._weekend_flag(
        {"boards": [{"weekendSession": "Y"}]}
    ) is True
    assert SpotUniverseService._weekend_flag({"WEEKENDSESSION": "unknown"}) is None


def test_weekend_universe_uses_official_moex_eligibility(monkeypatch):
    # MOEX's official WeekendSes mapping is the source of truth. This fixture
    # intentionally contradicts the BCS flags to ensure they cannot override it.
    monkeypatch.setattr(
        "services.spot_universe_service.MoexWeekendEligibilityService.load",
        lambda: {"WEEK", "BOARD"},
    )
    service = SpotUniverseService(api=FakeAPI())
    rows = service.load(weekend_session=True)

    assert {(row["spot_ticker"], row["spot_class_code"]) for row in rows} == {
        ("WEEK", "TQBR"),
        ("BOARD", "TQBR"),
    }


def test_weekend_universe_fails_closed_when_moex_mapping_is_unavailable(monkeypatch):
    monkeypatch.setattr(
        "services.spot_universe_service.MoexWeekendEligibilityService.load",
        lambda: None,
    )
    service = SpotUniverseService(api=FakeAPI())
    assert service.load(weekend_session=True) == []


def test_regular_universe_does_not_apply_weekend_eligibility_filter():
    service = SpotUniverseService(api=FakeAPI())
    rows = service.load(weekend_session=False)
    tickers = {row["spot_ticker"] for row in rows}
    assert tickers == {"WEEK", "NOPE", "BOARD", "UNKNOWN"}
