from services.two_phase_futures_morning_radar_service import TwoPhaseFuturesMorningRadarService


class _FakeSpotUniverse:
    def load(self):
        return [
            {"spot_ticker": "SBER", "spot_class_code": "SMAL", "spot_instrument_type": "STOCK"},
            {"spot_ticker": "SBER", "spot_class_code": "SPBRU", "spot_instrument_type": "STOCK"},
            {"spot_ticker": "SBER", "spot_class_code": "TQBR", "spot_instrument_type": "STOCK"},
            {"spot_ticker": "GAZP", "spot_class_code": "TQBR", "spot_instrument_type": "STOCK"},
            {"spot_ticker": "GAZP", "spot_class_code": "SPBRU", "spot_instrument_type": "STOCK"},
        ]


class _FakeIndex:
    def load(self):
        return {"SBER"}


class _FailingFuturesMapping:
    def load(self):
        raise AssertionError("futures mapping must not be loaded during SPOT universe discovery")


def _service():
    service = TwoPhaseFuturesMorningRadarService.__new__(TwoPhaseFuturesMorningRadarService)
    service.spot_universe_service = _FakeSpotUniverse()
    service.index_universe_service = _FakeIndex()
    service.mapping_service = _FailingFuturesMapping()
    return service


def test_direct_spot_universe_is_independent_from_futures_and_uses_canonical_tqbr():
    service = _service()
    spots = service._load_direct_spot_universe()
    assert [(item["spot_ticker"], item["spot_class_code"]) for item in spots] == [("SBER", "TQBR")]
    assert spots[0]["spot_universe"] == "IMOEX"
    assert spots[0]["mapping_method"] == "DIRECT_SPOT_UNIVERSE"


def test_non_tqbr_stock_boards_are_excluded_from_imoex():
    service = _service()
    spots = service._load_direct_spot_universe()
    assert all(item["spot_class_code"] == "TQBR" for item in spots)
    assert all(item["spot_ticker"] == "SBER" for item in spots)


def test_futures_mapping_is_not_called_for_waiting_spot_candidate():
    service = _service()
    service._attach_futures_after_spot(
        [{"spot_ticker": "SBER", "signal_state": "WAIT", "setup_state": "WAIT"}]
    )


def test_futures_mapping_is_deferred_until_spot_ready():
    class _Mapping:
        def load(self):
            return [{
                "spot_ticker": "SBER",
                "futures_ticker": "SBRF-10.26",
                "futures_class_code": "SPBFUT",
                "futures_expiry": "2026-10-15",
            }]

    class _Selector:
        def select(self, mappings):
            return mappings

    service = TwoPhaseFuturesMorningRadarService.__new__(TwoPhaseFuturesMorningRadarService)
    service.mapping_service = _Mapping()
    service.futures_contract_selector = _Selector()
    result = service._attach_futures_after_spot(
        [{
            "spot_ticker": "SBER",
            "signal_state": "READY",
            "setup_state": "READY",
        }]
    )
    assert result[0]["futures_ticker"] == "SBRF-10.26"
