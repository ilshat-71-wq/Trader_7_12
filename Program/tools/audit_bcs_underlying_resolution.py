from services.futures_oi_marketdata_scanner_service import FuturesOIMarketDataScannerService
from services.spot_universe_service import SpotUniverseService


UNRESOLVED = (
    "AFKS AFLT ALIBABA ALRS AMDF ASTR BAIDU BANE BELUGA BSPB BTC CBOM CNI COHRF FNI GAZPF HOME HOODF HYNIX IPO JDCOM KOREA LITEF MAGN MGNT MOEX MOEXCNY MTSI MVID NBISF NG NLMK NOVARTIS OGI OZON PDD PHOR POSI RAGR RASP RNFT ROSN RTKM RTS RUONIA S2 SAMSUNG SBERF SNDKF SNGP SOL SP500 SPY TATP TENCENT TOYOTA TRNF TRX TSLAF USDRUB WUSH X5 XIA XRP YDEX".split()
)


def main():
    scanner = FuturesOIMarketDataScannerService()
    if not scanner.api.authorize():
        raise SystemExit("BCS authorization failed")

    print("=== BCS SPOT UNDERLYING RESOLUTION AUDIT ===")
    rows = SpotUniverseService(api=scanner.api).load()
    by_ticker = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        ticker = str(row.get("spot_ticker") or "").upper()
        code = str(row.get("spot_class_code") or "")
        if ticker and code:
            by_ticker.setdefault(ticker, []).append((ticker, code, row.get("spot_instrument_type"), row.get("spot_group")))

    found = 0
    for ticker in UNRESOLVED:
        matches = by_ticker.get(ticker, [])
        if matches:
            found += 1
            print(f"{ticker}: {matches}")
        else:
            print(f"{ticker}: NOT_IN_SPOT_UNIVERSE")

    print("=== SUMMARY ===")
    print("spot_records:", len(rows))
    print("requested:", len(UNRESOLVED))
    print("found:", found)
    print("not_found:", len(UNRESOLVED) - found)
    print("=== END ===")


if __name__ == "__main__":
    main()
