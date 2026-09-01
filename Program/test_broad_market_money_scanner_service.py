from services.broad_market_money_scanner_service import BroadMarketMoneyScannerService


class _SpotUniverse:
    def load(self):
        return [
            {"spot_ticker": "SBER", "spot_class_code": "TQBR", "spot_instrument_type": "STOCK"},
            {"spot_ticker": "GAZP", "spot_class_code": "TQBR", "spot_instrument_type": "STOCK"},
            {"spot_ticker": "SBER", "spot_class_code": "SPBRU", "spot_instrument_type": "STOCK"},
            {"spot_ticker": "CBOM", "spot_class_code": "TQBR", "spot_instrument_type": "STOCK"},
            {"spot_ticker": "USD000SMALL", "spot_class_code": "CETS_FX", "spot_instrument_type": "CURRENCY"},
        ]


class _Session:
    def get_session(self):
        return "MAIN"

    def get_trading_day(self):
        return None


class _Money:
    VALUES = {"SBER": 3000.0, "GAZP": 1000.0, "CBOM": 2000.0}

    def calculate(self, ticker, class_code, **kwargs):
        value = self.VALUES[ticker]
        return {
            "money_volume": value,
            "money_per_minute": value / 10.0,
            "elapsed_minutes": 10,
            "expected_minutes": 180,
        }


def _service():
    return BroadMarketMoneyScannerService(_SpotUniverse(), _Money(), _Session())


def test_load_all_tqbr_stocks_uses_complete_canonical_stock_universe():
    stocks = _service().load_all_tqbr_stocks()
    assert [x["spot_ticker"] for x in stocks] == ["CBOM", "GAZP", "SBER"]
    assert all(x["spot_class_code"] == "TQBR" for x in stocks)
    assert all(x["spot_universe"] == "ALL_TQBR_STOCKS" for x in stocks)


def test_money_screen_ranks_all_stocks_by_current_session_money():
    ranked = _service().rank_current_money(force=True)
    assert [x["spot_ticker"] for x in ranked] == ["SBER", "CBOM", "GAZP"]
    assert [x["money_rank"] for x in ranked] == [1, 2, 3]
    assert ranked[0]["spot_session_money"] == 3000.0


def test_deep_stage_is_only_a_subset_after_full_money_screen():
    top = _service().top_for_deep_analysis(limit=2, force=True)
    assert [x["spot_ticker"] for x in top] == ["SBER", "CBOM"]
