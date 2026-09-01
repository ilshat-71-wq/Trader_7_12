from services.market_trading_universe_service import MarketTradingUniverseService


def test_macro_currency_futures_are_classified_without_fixed_single_ticker():
    assert MarketTradingUniverseService.futures_group("SIU6") == MarketTradingUniverseService.USDRUB
    assert MarketTradingUniverseService.futures_group("EURRUBF") == MarketTradingUniverseService.FX
    assert MarketTradingUniverseService.futures_group("CNYRUBF") == MarketTradingUniverseService.FX
    assert MarketTradingUniverseService.futures_group("KZTRUBF") == MarketTradingUniverseService.FX


def test_equity_group_remains_canonical_tqbr():
    assert MarketTradingUniverseService.spot_group({"spot_class_code": "TQBR"}) == "MOEX_STOCK"
