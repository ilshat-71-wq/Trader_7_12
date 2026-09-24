# Trader_7_12 Pro — ПАМЯТКА ПЕРЕХОДА В НОВЫЙ ЧАТ

Контрольная точка 24.09.2026. GitHub: ilshat-71-wq/Trader_7_12. Локально: ~/Documents/Trader_7_12. Приложение: ~/Applications/Trader_7_12 Pro.app. Последний подтверждённый commit: 3b1586da1fcc81df2abd7c8af92ad57fa926548b (Fix BCS WebSocket TLS CA verification).

REALTIME РАБОТАЕТ: BCS WebSocket → BOOK → TAPE → FLOW RT → UI. Подтверждено LIVE, Instruments 18, BOOK 18, TAPE 18. Тест: 8 passed, 1 warning. TLS через ssl.CERT_REQUIRED + certifi.where(); проверку сертификата не отключать.

Примеры: OZON 47/23/35; GLDRUB_TOM 66/42/54; CNYRUB 60/60/60; BR 54/65/60; NG 50/83/66; GL 55/17/36. SPOT: CNTLP 72/100/86; CNTL 19/63/41; UKUZ 41/100/70; KLVZ 41/100/70; RBCM 31/100/65; PLZL 68/35/51.

— означает отсутствие realtime-снимка, а не нулевой поток. SIGNAL модели и realtime — разные слои; realtime не переписывает D1/M5 SIGNAL.

SPOT: STATUS OK, MAIN, 2026-09-24, REGIME DOWN, Universe 261, Analyzed 251, Coverage 96.2%, D1 qualified 2, Directional qualified 1, Strict 1, Watch 19, Context 0, Map 251, Stronger 156, Weaker 95, Total 109.996s.

INTEREST: REGIME NEUTRAL, IMOEX2 -0.0585%, Interest ↑3, SHORT WATCH 0, Persistent Short 0, Snapshots 3, OI 8, FLOW 6, HOT LIQ 6. SHORT WATCH — отдельная weakness lane.

НЕ МЕНЯТЬ СЕЙЧАС: сначала наблюдать несколько циклов — меняются ли BOOK; появляется ли TAPE; меняется ли FLOW RT; сохраняется ли LIVE после reconnect; не возвращается ли TLS error. Не править realtime-код только из-за отдельных TAPE —.

Ключевые commits: 8f0794a — shutdown/reconnect; 937a578c... — realtime checkpoint/auth/mapping/subscriptions; 16874ffa... — diagnostics tests; 3b1586d... — TLS CA fix.

Mapping: GZ→GAZP; SR→SBER; RI→RTS; SI→USDRUB; EU→EURRUB; CR/CNY→CNYRUB; GD→GLDRUB_TOM; MX/MM→IMOEX; IMOEXF→IMOEX; NGU6/NG-09.26→FEG/NGas1026; NGZ6/NG-12.26→FEG/NGas1026; SIZ6→USD000SMALL; USDRUBF→CETS_FX/USD000SMALL; EURRUB→EUR_RUB__TOM/CETS. USDRUBF не использовать как реальный spot/base вместо USD000SMALL.

Быстрая сборка: cd ~/Documents/Trader_7_12 && git pull --ff-only origin main && python3 -m pytest -q Program && ./scripts/build_mac_app.sh && rm -rf "$HOME/Applications/Trader_7_12 Pro.app" && cp -R "dist/Trader_7_12 Pro.app" "$HOME/Applications/Trader_7_12 Pro.app" && open "$HOME/Applications/Trader_7_12 Pro.app"

Статус: 🟢 REST auth; 🟢 WebSocket TLS; 🟢 LIVE; 🟢 BOOK; 🟢 TAPE; 🟢 FLOW RT; 🟢 SPOT UI realtime; 🟢 Futures OI; 🟢 SPOT Radar; 🟢 приложение собрано/установлено; 🟡 наблюдение стабильности.

Правило нового чата: читать эту памятку как контрольную точку; не откатывать TLS-фикс; одна диагностика → анализ → минимальный фикс → тест → сборка → наблюдение.