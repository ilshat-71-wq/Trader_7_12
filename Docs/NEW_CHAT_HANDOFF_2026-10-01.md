# TRADER_7_12 PRO — NEW CHAT HANDOFF

**Дата актуализации:** 11.10.2026  
**Репозиторий:** `ilshat-71-wq/Trader_7_12`  
**Рабочая ветка:** `main`  
**Кодовый checkpoint GitHub main:** `ee7fef4cf92959b639f1cc44f0ea6eaaf68dba6c`  
**Последний ранее подтверждённый функциональный checkpoint:** `15273355d530b6d4f211725faf6c4a912881305f`

## 1. Как продолжать

Это существующий проект. Не переписывать архитектуру, не создавать новый scanner, не делать новый проект.

Рабочий порядок:

```
изменение
→ тесты
→ реальная проверка
→ commit
→ main
→ обновить PROJECT_PASSPORT.md
→ pull
→ build
→ открыть Trader_7_12 Pro.app
→ проверить приложение
```

Правила:
- русский, кратко и практически;
- copy-ready terminal commands;
- без `nano`;
- не говорить «готово» до проверки;
- REAL BCS DATA ONLY;
- `NO DATA / INCOMPLETE / NO TRADE`;
- никакой синтетики;
- не выдумывать OI, Money Flow, цены, тикеры, expiries или classCode;
- BCS credentials не помещать в docs/source;
- realtime только подтверждает сигнал и не переписывает D1/M5 semantics;
- никаких order execution / portfolio management / position sizing / SL-TP execution.

## 2. Главный текущий checkpoint

Исправлена критическая ошибка benchmark:

```python
BENCHMARKS = ("IMOEX", "IRUS2")
```

Было ошибочно:

```python
BENCHMARKS = ("IMOEX2", "IRUS2")
```

Реальный BCS benchmark подтверждён:

```
ticker = IMOEX
classCode = INDX
D1 candles = 28
BCS authorization = OK
```

GitHub commit:

```
15273355d530b6d4f211725faf6c4a912881305f
Fix Radar benchmark to real IMOEX index
```

## 3. D1 уже доказан на реальных данных

Напрямую протестирован `DailyTrendProfileService 2.2`:

```
ARSA  LONG   3 days   +16.56%   STRONGER   qualified=True
OZON  LONG   3 days    +3.44%   STRONGER   qualified=True
LKOH  LONG   3 days    +3.05%   STRONGER   qualified=True
GMKN  SHORT  3 days    -2.09%   WEAKER     qualified=True
```

Это означает:

```
BCS TQBR D1
→ real IMOEX / INDX D1
→ D1 structure
→ relative strength
→ LONG / SHORT
→ qualified
```

работает.

## 4. Что ещё НЕ доказано

Production:

```
MarketAttentionScannerService.scan()
→ D1
→ H1
→ M5
→ M1
→ production Radar
```

ещё не подтверждён в открытой торговой сессии.

Ночная проверка дала:

```
session = CLOSED
market_open = False
session_start = None
scan() = []
```

Это нормально и не считается дефектом.

**Следующий обязательный live check — только в открытом рынке.**

## 5. Следующий шаг нового чата

Не менять код сразу.

В открытой торговой сессии сначала запустить production scanner и проверить:

1. появляются ли D1-qualified rows;
2. сохраняется ли D1 direction;
3. проходят ли они в H1;
4. затем M5;
5. затем M1 entry;
6. только после этого проверять UI/Entry Radar.

Не ослаблять gates ради появления кандидатов.

## 6. Realtime checkpoint

Технически подтверждено:

```
SUBSCRIBED = 100
BOOK = 100/100
TAPE = 100/100
BCS protocol acknowledgements = OK
```

Realtime не должен менять D1 direction.

## 7. Tests

Последняя подтверждённая полная проверка:

```
197 passed, 1 warning
```

Warning — pytest-asyncio deprecation на Python 3.14, не market-data failure.

## 8. Важное локальное состояние iMac

На момент передачи был обнаружен незакоммиченный локальный файл:

```
M Program/test_daily_trend_profile_service.py
```

Не удалять и не коммитить вслепую.

Сначала:

```bash
cd ~/Documents/Trader_7_12
git status --short --branch
git diff -- Program/test_daily_trend_profile_service.py
```

После понимания изменения — отдельно решить, сохранить его или отклонить.

## 9. Синхронизация после этого passport commit

GitHub получил обновление паспорта и эту памятку.

Перед локальной сборкой:

```bash
cd ~/Documents/Trader_7_12 && \
git fetch origin && \
git switch main && \
git status --short --branch && \
git log -1 --oneline
```

**Не делать `git reset --hard`**, пока не разобран локальный `Program/test_daily_trend_profile_service.py`.

После безопасной синхронизации:

```
pytest
→ real live check
→ build
→ open Trader_7_12 Pro.app
→ app check
```

## 10. Canonical documents

Главный паспорт:

```
Docs/PROJECT_PASSPORT.md
```

Эта памятка:

```
Docs/NEW_CHAT_HANDOFF_2026-10-01.md
```

Новый чат начинать с GitHub `main` + этих двух документов.

**Не использовать память чата как единственный источник состояния проекта.**


## АКТУАЛЬНАЯ ПЕРЕДАЧА — 11.10.2026

### Источник и документация
- Канонический кодовый checkpoint перед синхронизацией документации: `ee7fef4cf92959b639f1cc44f0ea6eaaf68dba6c` (`Fix weekend SPOT eligibility CI`).
- Паспорт актуализирован отдельным документационным commit `68ebfee42734ef76154c7db0444453883880dc41`; этот handoff обновляется следом. После обновления обоих файлов точный GitHub HEAD проверить через `git log -1 --oneline` или на странице репозитория — документационные commits не меняют кодовый checkpoint.
- CI status connector не показал записей, поэтому CI PASS для `ee7fef4` не заявляем. Локальный полный pytest/build на iMac после этого checkpoint также не подтверждён.
- Последний ранее упомянутый локальный diff `Program/test_daily_trend_profile_service.py` нужно проверить на самой машине; его актуальное наличие неизвестно. Никаких `reset --hard`, очистки и принудительного pull до просмотра diff.

### Последний наблюдавшийся runtime — воскресенье, 11.10.2026
- Cloud health READY, snapshot version 14, последняя SPOT-сессия `WEEKEND_SESSION`, scan завершился без last_scan_error.
- SPOT: universe 255, analyzed 233, coverage 91.4%, liquidity passed 91, D1 qualified 19, directional qualified 7, strict 7, watch 13, selected 20; total scan ~353.1 s.
- Futures OI 8/8; Money Flow `NO_DATA`; realtime 100 subscribed, BOOK 100, TAPE 100.
- FINAL: `NEED 3 MORE SCANS`, scan 5, strict 0, final SPOT 0, final Futures 0, RT READY 0, RT BLOCKED 0.
- Это подтверждает запуск воскресного контура, но не подтверждает торговый сигнал и не заменяет проверку в обычную открытую сессию.

### Завтра, понедельник 12.10.2026 — порядок проверки
1. На iMac: проверить локальный статус и diff; сохранить нужные локальные изменения, затем синхронизировать `main` fast-forward only.
2. Compile + full pytest. Не переносить старый результат `197 passed` на новый commit без повторного запуска.
3. При успешных тестах — собрать `Trader_7_12 Pro.app`, открыть установленную сборку и сверить её commit/build с исходником.
4. Проверить Cloud endpoints и один полный цикл обновления.
5. Во время реальной торговой сессии записать D1 → H1 → M5 → M1/ENTRY, Futures OI, Money Flow, realtime BOOK/TAPE/FLOW RT и FINAL confirmation sequence.
6. Не менять фильтры и пороги ради появления кандидатов; отсутствующие реальные данные оставлять `NO DATA / INCOMPLETE / NO TRADE`.

### Безопасная первичная диагностика iMac
```bash
cd ~/Documents/Trader_7_12
git status --short --branch
git diff -- Program/test_daily_trend_profile_service.py
git fetch origin
git log -1 --oneline
git log -1 --oneline origin/main
```

Только после просмотра вывода выбираем безопасный способ синхронизации. Если локальное дерево чистое:
```bash
git switch main
git pull --ff-only origin main
git status --short --branch
git log -1 --oneline
```

После pull:
```bash
python3 -m compileall -q Program
python3 -m pytest -q
```

Только при успешных тестах:
```bash
./scripts/build_mac_app.sh
open "$HOME/Applications/Trader_7_12 Pro.app"
```

