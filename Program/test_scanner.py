from scanner.scanner_engine import ScannerEngine


print("🚀 Запуск теста сканера")


scanner = ScannerEngine()


rows = scanner.scan()


print()
print("==============================")
print("Всего инструментов:", len(rows))
print("==============================")
print()


for row in rows[:20]:

    print(
        row.ticker,
        "| Цена:",
        row.last,
        "| Объём:",
        row.volume,
        "| Оборот:",
        row.money_volume,
        "| Rating:",
        row.rating,
    )