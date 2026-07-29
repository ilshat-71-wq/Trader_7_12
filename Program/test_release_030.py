from scanner.scanner_engine import ScannerEngine


scanner = ScannerEngine()

rows = scanner.scan()

print()
print("=" * 90)
print(
    f"{'Ticker':8} "
    f"{'Last':>10} "
    f"{'%':>8} "
    f"{'Volume':>12} "
    f"{'Money':>15} "
    f"{'Rate':>6}"
)
print("=" * 90)

for row in rows:

    print(
        f"{row.ticker:8} "
        f"{row.last:10.2f} "
        f"{row.change:8.2f} "
        f"{row.volume:12,.0f} "
        f"{row.money_volume:15,.0f} "
        f"{row.rating:6}"
    )

print("=" * 90)
print(f"Всего инструментов: {len(rows)}")