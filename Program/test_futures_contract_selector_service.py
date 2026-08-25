"""Offline tests for futures contract selection."""

from services.futures_contract_selector_service import FuturesContractSelectorService


class FakeAPI:
    def __init__(self):
        self.quotes = {
            "NU6": {"ticker": "NU6", "classCode": "SPBFUT", "bid": 100.0, "offer": 100.1, "last": 100.05},
            "NZ6": {"ticker": "NZ6", "classCode": "SPBFUT", "bid": 101.0, "offer": 101.8, "last": 101.4},
        }
        self.books = {
            "NU6": {
                "bids": [{"price": 100.0, "quantity": 1000}],
                "asks": [{"price": 100.1, "quantity": 1000}],
            },
            "NZ6": {
                "bids": [{"price": 101.0, "quantity": 10}],
                "asks": [{"price": 101.8, "quantity": 10}],
            },
        }
        self.trades = {
            "NU6": {"records": [{"price": 100.0, "quantity": 1000}] * 20},
            "NZ6": {"records": [{"price": 101.0, "quantity": 10}] * 20},
        }

    def get_quotes(self, instruments):
        return {"records": [self.quotes[item["ticker"]] for item in instruments if item["ticker"] in self.quotes]}

    def get_order_book(self, ticker, class_code):
        return self.books.get(ticker, {})

    def get_last_trades(self, ticker, class_code):
        return self.trades.get(ticker, {"records": []})


def test_selector_prefers_liquid_near_contract():
    selector = FuturesContractSelectorService(api=FakeAPI())
    mappings = [
        {
            "spot_ticker": "NLMK",
            "spot_class_code": "TQBR",
            "futures_ticker": "NU6",
            "futures_class_code": "SPBFUT",
            "futures_expiry": "2099-09-17",
        },
        {
            "spot_ticker": "NLMK",
            "spot_class_code": "TQBR",
            "futures_ticker": "NZ6",
            "futures_class_code": "SPBFUT",
            "futures_expiry": "2099-12-17",
        },
    ]
    result = selector.select(mappings)
    assert len(result) == 1
    assert result[0]["futures_ticker"] == "NU6"
    assert result[0]["spread_percent"] < 0.2
    assert result[0]["turnover_30m"] > result[0]["futures_ticker"].count("Z")
    assert result[0]["selection_score"] > 0


def test_selector_rejects_expiring_contracts():
    selector = FuturesContractSelectorService(api=FakeAPI())
    mappings = [{
        "spot_ticker": "NLMK",
        "spot_class_code": "TQBR",
        "futures_ticker": "NU6",
        "futures_class_code": "SPBFUT",
        "futures_expiry": "2026-08-27",
    }]
    assert selector.select(mappings) == []


if __name__ == "__main__":
    test_selector_prefers_liquid_near_contract()
    print("PASS test_selector_prefers_liquid_near_contract")
    test_selector_rejects_expiring_contracts()
    print("PASS test_selector_rejects_expiring_contracts")
    print("ALL TESTS PASSED")
