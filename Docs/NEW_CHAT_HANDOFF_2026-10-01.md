# TRADER_7_12 PRO — NEW CHAT HANDOFF

**Дата:** 01.10.2026  
**Репозиторий:** `ilshat-71-wq/Trader_7_12`  
**Рабочая ветка:** `main`  
**GitHub main:** `bbdc9ec9fa42b8a2cc9542be26b418c5e533b68b`  
**Предыдущий функциональный checkpoint:** `15273355d530b6d4f211725faf6c4a912881305f`

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
