from services.futures_spot_mapping_service import FuturesSpotMappingService
from services.stage1_mapping_diagnostic import Stage1MappingDiagnostic


def spot(ticker, class_code="TQBR"):
    return {"ticker": ticker, "classCode": class_code, "shortName": ticker}


def future(ticker, **fields):
    item = {
        "ticker": ticker,
        "classCode": "SPBFUT",
        "expiry": "2099-12-01",
    }
    item.update(fields)
    return item


def test_nested_bcs_underlying_maps_exactly():
    service = FuturesSpotMappingService()
    diagnostic = Stage1MappingDiagnostic(service)

    result = diagnostic.analyze(
        [
            future(
                "TESTZ9",
                baseAssetSecurity={
                    "securityCode": "TEST",
                    "classCode": "TQBR",
                },
            )
        ],
        [spot("TEST")],
    )

    assert result["mapped"] == 1
    assert result["unmapped"] == 0
    assert result["mapped_rows"][0]["mapping_method"] == "BCS_UNDERLYING"


def test_missing_underlying_is_explained():
    service = FuturesSpotMappingService()
    diagnostic = Stage1MappingDiagnostic(service)

    result = diagnostic.analyze([future("UNKNOWNZ9")], [spot("OTHER")])

    assert result["mapped"] == 0
    assert result["failure_counts"]["NO_UNDERLYING_METADATA"] == 1


def test_explicit_underlying_not_in_spot_is_distinguished():
    service = FuturesSpotMappingService()
    diagnostic = Stage1MappingDiagnostic(service)

    result = diagnostic.analyze(
        [future("TESTZ9", baseAssetSecuritySecCode="TEST")],
        [spot("OTHER")],
    )

    assert result["mapped"] == 0
    assert result["failure_counts"]["EXPLICIT_UNDERLYING_NOT_IN_SPOT"] == 1
