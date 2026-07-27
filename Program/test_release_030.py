from scanner.scanner_engine import ScannerEngine

scanner = ScannerEngine()

rows = scanner.scan()

print()
print("========== TOP ==========")

for row in rows[:20]:
    print(
        f"{row.ticker:8} "
        f"{row.last:10} "
        f"{row.change:8} "
        f"Vol={row.volume:12,.0f} "
        f"Money={row.money_volume:15,.0f}"
    )