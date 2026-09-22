# Trader_7_12 Pro — Паспорт проекта / переход в новый чат
Дата: 23.09.2026
Репозиторий: https://github.com/ilshat-71-wq/Trader_7_12
Ветка: main

## 1. Правило продолжения

Это существующий проект Trader_7_12 Pro. НЕ начинать заново, НЕ создавать отдельное приложение и НЕ переносить функциональность в новый проект.

Едиственное desktop-приложение:
`Trader_7_12 Pro.app`

Основной принцип:
- реальные данные MOEX/BCS;
- никаких synthetic Price×Volume;
- никаких подмен отсутствующего базового инструмента фьючерсом;
- read-only аналитика, без торгового исполнения;
- WATCH не считать полноценной торговой рекомендацией;
- PROB не называть математической вероятностью без проверки формулы;
- перед существенными изменениями запускать тесты;
- после изменений синхронизировать GitHub -> iMac -> build.

## 2. Текущая архитектура

### Desktop
`Program/`
- SPOT / MARKET RADAR
- MORNING RADAR
- FUTURES OI / REAL MONEY FLOW
- Diagnostics
- Settings

### Cloud
`Cloud/`
- локальный Cloud Market Data Engine
- `/health`
- `/v1/status`
- `/v1/snapshot`
- `/v1/morning-radar`
- `/v1/scan`
- `/v1/stream`

Cloud не является отдельным desktop-приложением.

## 3. SPOT / Market Radar

Текущий рынок:
- SPOT base only;
- MOEX stocks;
- D1 + M5;
- benchmark IMOEX2;
- relative strength;
- liquidity;
- directional qualification;
- strict LONG/SHORT selection;
- WATCH отдельно.

На последнем закрытом снимке:
- trading_date: 2026-09-23
- market_session: CLOSED
- universe_total: 0, потому что рынок закрыт и текущий снимок не выполнял SPOT intraday scan.

В рабочую торговую сессию радар должен анализировать весь доступный universe, а не фиксированные 20/30 акций.

## 4. Morning Radar

Интегрирован в Trader_7_12 Pro.

Слоты MSK:
- 07:00
- 07:15
- 07:30
- 08:00
- 09:00
- 09:45
- 09:50

Хранение:
`Cloud/data/morning_radar`
- JSON по торговым датам;
- atomic write;
- хранение до 14 дней.

Отслеживает:
- market regime;
- benchmark;
- interest RISING/FALLING/STABLE/NEW;
- money/minute;
- recent money/minute;
- acceleration;
- relative strength;
- countertrend watch;
- persistence по утренним слотам.

Morning Radar не блокирует ручной scan.

## 5. Ручное сканирование

Пользователь может запускать обычный scan в любое время, когда есть доступные данные.

Morning Radar — дополнительный автоматический слой, а не замена ручному сканированию.

Вне торговой сессии допустимый результат:
`MARKET_CLOSED`

## 6. Futures OI

Источник:
- MOEX RFUD / futures marketdata;
- OI primary;
- exact expiry D-3 calendar-day rollover;
- без fallback на истекающий контракт.

Разрешённые семейства:
- Russian single-stock futures
- USDRUB
- EURRUB
- CNYRUB
- Brent
- CL
- NG
- Gold

Последний снимок 23.09.2026:
- raw contracts: 503
- active contracts: 8
- active roots: 8
- analyzed: 8
- OI available: 8
- liquidity available: 8
- turnover source: VALTODAY_ONLY
- synthetic Price×Volume: запрещён
- data quality: COMPLETE
- base-change intraday вне торговой сессии: 0/8

## 7. BCS underlying mapping

Используется canonical BCS underlying + MOEX RFUD family mapping.

Известные реальные соответствия:
- NGU6 / NG-09.26 -> FEG / NGas1026
- NGZ6 / NG-12.26 -> FEG / NGas1026
- SIZ6 -> USD000SMALL
- USDRUBF может существовать как metadata/reference, но не использоваться как реальный market-data base вместо USD000SMALL.
- EURRUB: `EUR_RUB__TOM` / CETS; не подменять фьючерсом.

Текущее mapping:
- underlying mapping exact: 7
- semantic: 0
- unresolved: 0
- supported base: 7
- supported base mapped: 8
- futures-only: 1

## 8. Money Flow

Текущий основной flow:
- BCS last trades 30m
- current order book
- liquidity window 5m
- real BCS data only
- no participant identity claims.

Если данных нет:
`NO_DATA`, а не синтетическое значение.

## 9. НОВОЕ: realtime BOOK + TAPE

Добавлен модуль:
`Program/services/realtime_microstructure_service.py`

Источник:
`BCS_WEBSOCKET_MARKET_DATA`

Назначение:
- real Level-2 order book;
- до 20 уровней;
- real anonymized trades;
- realtime updates;
- read-only.

Новые поля:
- BOOK
- TAPE
- FLOW RT

Смысл:
- BOOK = observed bid/ask imbalance;
- TAPE = observed BUY/SELL trade-flow imbalance;
- FLOW RT = объединённая оценка BOOK + TAPE.

Это не математическая вероятность и не идентификация участников рынка.

Подписка ограничивается рабочим набором:
- active futures;
- SPOT — только отобранные кандидаты, не весь universe;
- технический максимум сервиса: 100 инструментов.

## 10. Важное состояние realtime

Realtime-код добавлен в GitHub, но на iMac ещё ОБЯЗАТЕЛЬНО нужно:
1. `git pull --ff-only origin main`
2. установить `websocket-client`, если пакета нет;
3. выполнить полный `pytest -q Program`;
4. собрать приложение;
5. проверить реальное подключение BCS во время торговой сессии.

До такого теста не считать realtime BOOK/TAPE полностью подтверждённым production runtime.

## 11. OI UI

Зелёная строка:
- только top-5 по реальному текущему дневному денежному обороту;
- источник MOEX VALTODAY;
- не Price×Volume.

DAY ₽:
- поддерживает сортировку значений с B/M/K suffix;
- например 152.08B, 128.23B и т.д.

Premium signal:
- 🟢 LONG
- 🔴 SHORT
- ⚪ NEUTRAL

## 12. Morning Radar autostart

Добавлен:
`scripts/install_cloud_launch_agent.sh`

LaunchAgent:
`~/Library/LaunchAgents/com.ilshat.trader712.cloud.plist`

Cloud запускается локально на:
`127.0.0.1:8080`

RunAtLoad + KeepAlive.

ВАЖНО:
launchd работает только пока Mac включён/доступен. Это не удалённый облачный сервер.

## 13. Build

Bundle:
`dist/Trader_7_12 Pro.app`

Install:
`~/Applications/Trader_7_12 Pro.app`

Последняя подтверждённая версия до realtime:
- Bundle version 2.4.3
- ad-hoc signed
- PyInstaller onedir + macOS .app

После realtime необходимо подтвердить новую сборку на iMac.

## 14. Стандартная синхронизация iMac

Для Trader_7_12 Pro:

```bash
cd ~/Documents/Trader_7_12 && \
git pull --ff-only origin main && \
python3 -m pip install websocket-client && \
python3 -m pytest -q Program && \
./scripts/build_mac_app.sh && \
open "dist/Trader_7_12 Pro.app"
```

После этого:
```bash
cd ~/Documents/Trader_7_12 && \
git status --short && \
git log -1 --oneline
```

Рабочее дерево должно быть clean.

## 15. Автозапуск Cloud — один раз

Если ещё не выполнено:

```bash
cd ~/Documents/Trader_7_12 && \
chmod +x scripts/install_cloud_launch_agent.sh && \
./scripts/install_cloud_launch_agent.sh
```

Ожидаемый вывод:
`=== TRADER_7_12 CLOUD AUTOSTART INSTALLED ===`

## 16. Тесты realtime

Добавлен:
`Program/test_realtime_microstructure_service.py`

Проверяет:
- расчёт BOOK imbalance;
- нейтральный TAPE;
- ограничение realtime subscription.

Полный тест:
```bash
python3 -m pytest -q Program
```

## 17. Последние изменения GitHub

Realtime commits:
- `5569b36` — Add BCS realtime order book and tape service
- `8f3a5b0` — Add realtime microstructure columns to SPOT radar
- `1af05e4` — Require websocket-client for realtime market data build
- `5ec6e61` — Package realtime BCS WebSocket dependency
- `cc5a722` — Add realtime microstructure regression tests
- `57caf47` — Show realtime BOOK TAPE in dashboard subtitle

После этих коммитов нужен локальный iMac test/build.

## 18. Финансовая цель проекта

Изначальная практическая цель пользователя:
- депозит: 7,000,000 ₽;
- ориентир: стремиться к 20,000 ₽ в день;
- фокус: первая половина торгового дня;
- приоритет: часы наиболее активной торговли на MOEX.

Эта цель является ориентиром пользователя, а приложение должно предоставлять проверенные рыночные данные и аналитику, а не обещать доходность.

## 19. Главный принцип следующего этапа

Следующий этап после успешного iMac runtime-теста:

**SPOT/D1/M5 → liquidity/RS → OI → real-time BOOK → real-time TAPE → FLOW RT → итоговая microstructure оценка.**

Не менять существующие D1/M5/OI расчёты без измерений.

Сначала доказать:
1. BCS realtime authorization;
2. live OrderBook;
3. live LastTrades;
4. корректное сопоставление ticker + classCode;
5. отсутствие synthetic data;
6. устойчивый reconnect;
7. корректное обновление UI;
8. отсутствие утечек/зависаний;
9. полный pytest;
10. успешный macOS build.

После этого можно разрабатывать более продвинутую оценку стакана/ленты.

## 20. Контекст для нового чата

Фраза для продолжения:

"Продолжаем Trader_7_12 Pro. Прочитай Docs/TRADER_7_12_PASSPORT_2026-09-23.md и продолжай строго с текущей точки. Проект не начинать заново. Сначала проверь состояние Git/iMac и результаты полного pytest/build. Главная текущая задача — подтвердить реальный BCS WebSocket BOOK/TAPE и только после этого развивать microstructure scoring."
