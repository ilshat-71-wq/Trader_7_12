"""Trader_7_12 Pro — canonical SPOT + separate macro watchlist UI."""

from html import escape

from ui import (
    TraderWindow,
    DIRECTION_LABELS,
    SETUP_LABELS,
    SETUP_STATE_LABELS,
    SESSION_LABELS,
    _label,
    _money,
    _number,
    _rs_label,
    _activity_label,
)


SIGNAL_STATE_LABELS = {
    "WAIT": "ОЖИДАНИЕ",
    "READY": "ГОТОВ — ТРИГГЕР АКТИВЕН",
    "CONFIRMED": "ПОДТВЕРЖДЁН SPOT",
    "ARMED": "ТРИГГЕР ВЗВЕДЁН — ЖДЁМ АКТИВАЦИЮ",
}

REASON_LABELS = {
    "SPOT setup is not ready": "SPOT-сетап ещё не сформирован",
    "trigger active; waiting for stability": "триггер активен; ожидаем стабильность",
    "SPOT setup is armed and the directional trigger is active": "SPOT-сетап сформирован и направленный триггер активен",
    "—": "—",
}

REJECTION_LABELS = {
    "NO_DIRECTION": "нет подтверждённого направления LONG/SHORT",
    "EVENT_RISK": "обнаружен event-risk",
    "RS_UNAVAILABLE": "Relative Strength недоступен",
    "RS_AGAINST_LONG": "RS не подтверждает LONG",
    "RS_AGAINST_SHORT": "RS не подтверждает SHORT",
    "WRONG_SPOT_GROUP": "инструмент не относится к целевой SPOT-группе",
    "SETUP_DATA_ERROR": "ошибка или отсутствие данных для SPOT-сетапа",
    "INVALID_SETUP_STATE": "некорректное состояние сетапа",
    "INVALID_RADAR": "некорректный результат радара",
}


def _signal_reason(value):
    text = str(value or "—")
    return REASON_LABELS.get(text, text)


def _rejection_reason(value):
    text = str(value or "—")
    return REJECTION_LABELS.get(text, text)


def _scenario_grade(score):
    try:
        value = float(score or 0)
    except (TypeError, ValueError):
        value = 0.0
    if value >= 75:
        return "ОЧЕНЬ СИЛЬНЫЙ"
    if value >= 60:
        return "СИЛЬНЫЙ"
    if value >= 45:
        return "СРЕДНИЙ"
    return "СЛАБЫЙ"


def _action_label(signal_state, trigger_active):
    state = str(signal_state or "WAIT").upper()
    if state == "CONFIRMED":
        return "СЦЕНАРИЙ ПОДТВЕРЖДЁН — РЕШЕНИЕ О ВХОДЕ ПРИНИМАЕТ ПОЛЬЗОВАТЕЛЬ"
    if state == "READY":
        return "СЦЕНАРИЙ ГОТОВ — ПРОВЕРИТЬ ТОЧКУ ВХОДА И РИСК"
    if trigger_active:
        return "НАБЛЮДАТЬ — ТРИГГЕР ЕСТЬ, НО НУЖНА СТАБИЛЬНОСТЬ"
    return "ЖДАТЬ — ТРИГГЕР НЕ АКТИВЕН"


class WatchlistTraderWindow(TraderWindow):
    """Read-only GUI bound to the SPOT-first watchlist contract."""

    VERSION = "1.9"

    def __init__(self, scanner_enabled=True):
        super().__init__(scanner_enabled=scanner_enabled)
        self.setWindowTitle("Trader_7_12 Pro — радар возможностей")
        self.subtitle.setText("SPOT • MONEY • НАПРАВЛЕНИЕ • RS • СЕТАП • ТРИГГЕР • ГОТОВНОСТЬ • MACRO WATCH")

    def _scan_finished(self, results):
        self.scan_button.setEnabled(True)
        self._stop_scan_animation()

        info = self.session_service.get_session_info()
        session = info.get("session", "CLOSED")
        session_name = SESSION_LABELS.get(session, session)

        diagnostics = {}
        if self.scanner is not None:
            diagnostics = getattr(self.scanner, "_last_scan_diagnostics", {}) or {}
        if results and isinstance(results[0], dict):
            diagnostics = results[0].get("scan_diagnostics") or diagnostics

        results = [
            item for item in (results or [])
            if str(item.get("analysis_source") or "SPOT").upper() != "FUTURES_DIRECT"
        ]

        lines = [
            "<pre style='font-family:Menlo,Monaco,monospace;font-size:14px;color:#dfe3e7'>",
            "═" * 86,
            "TRADER_7_12 PRO — РАДАР ВОЗМОЖНОСТЕЙ",
            "═" * 86,
            "",
            f"{session_name} • {info.get('date','—')} • МСК {info.get('time','—')}",
            "",
            "ГДЕ ДЕНЬГИ • ГДЕ СИЛА/СЛАБОСТЬ • ГДЕ СФОРМИРОВАЛСЯ SPOT-СЦЕНАРИЙ",
            "",
        ]

        leaders = diagnostics.get("active_money_leaders", []) if diagnostics else []
        if leaders:
            lines.extend([
                "",
                "████  TOP ACTIVE MONEY — TQBR  ████",
                "",
                f"{'RANK':>4}  {'TICKER':<10} {'SESSION ₽×V':>18} {'₽×V/МИН':>16}",
                "-" * 58,
            ])
            for row in leaders:
                lines.append(
                    f"{int(row.get('rank') or 0):>4}  "
                    f"{escape(str(row.get('spot_ticker') or '—')):<10} "
                    f"{_money(row.get('spot_session_money')):>18} "
                    f"{_money(row.get('spot_money_per_minute')):>16}"
                )
            lines.extend([
                "",
                "Это текущая денежная активность рынка. Она НЕ является сигналом LONG/SHORT.",
                "Следующий этап: направление → RS → сетап → триггер → стабильность.",
                "",
                "─" * 86,
            ])

        macro_watch = diagnostics.get("macro_watch", []) if diagnostics else []
        if macro_watch:
            lines.extend([
                "",
                "████  MACRO / FUTURES WATCH — ОТДЕЛЬНО  ████",
                "",
                "Это наблюдение за OIL/GOLD/GAS/FX. Эти контракты НЕ являются SPOT-кандидатами основного рейтинга.",
                "",
            ])
            for row in macro_watch:
                direction = _label(DIRECTION_LABELS, row.get("direction"))
                lines.append(
                    f"{int(row.get('rank') or 0):>3}. "
                    f"{escape(str(row.get('ticker') or '—')):<10} "
                    f"{direction:<8} "
                    f"money={_money(row.get('session_money')):>16} "
                    f"pace={_money(row.get('money_per_minute')):>12} "
                    f"score={_number(row.get('score'), 1):>6}"
                )
            lines.extend([
                "",
                "MACRO/FUTURES WATCH не участвует в SPOT trade ranking и не даёт торговую команду.",
                "─" * 86,
            ])

        if not results:
            lines.extend([
                "",
                "НЕТ SPOT-КАНДИДАТОВ В СПИСКЕ НАБЛЮДЕНИЯ",
                "",
                "В текущей сессии нет SPOT-активов, прошедших обязательные проверки отбора.",
                "Но TOP ACTIVE MONEY выше показывает, где сейчас находится основная активность.",
            ])
        else:
            for idx, item in enumerate(results, start=1):
                source_label = "SPOT / TQBR"
                direction = _label(DIRECTION_LABELS, item.get("direction"))
                setup = _label(SETUP_LABELS, item.get("setup"))
                setup_state = _label(SETUP_STATE_LABELS, item.get("setup_state"))
                signal_state_raw = str(item.get("signal_state") or "WAIT").upper()
                signal_state = SIGNAL_STATE_LABELS.get(signal_state_raw, "ОЖИДАНИЕ")
                rs = _rs_label(item)
                opportunity = item.get("opportunity_score", item.get("session_rank_score", 0))
                trigger_present = bool(item.get("trigger_present"))
                trigger_active = bool(item.get("trigger_active"))
                activity_label = _activity_label(item)

                lines.extend([
                    "",
                    f"████  #{idx}  {escape(str(item.get('spot_ticker') or '—'))}  ████",
                    f"ИСТОЧНИК:           {source_label}",
                    f"НАПРАВЛЕНИЕ:       {direction}",
                    f"ОЦЕНКА ВОЗМОЖНОСТИ: {_number(opportunity, 1)} / 100",
                    f"СИЛА СЦЕНАРИЯ:     {_scenario_grade(opportunity)}",
                    f"ОЦЕНКА СЕССИИ:     {_number(item.get('session_rank_score'), 1)} / 100",
                    f"RS:                 {rs}",
                    f"АКТИВНОСТЬ:         {activity_label}",
                    f"СЕТАП:              {setup}",
                    f"СОСТОЯНИЕ СЕТАПА:   {setup_state}",
                    f"СОСТОЯНИЕ СИГНАЛА:  {signal_state}",
                    f"РЕКОМЕНДАЦИЯ:       {_action_label(signal_state_raw, trigger_active)}",
                    "",
                    f"ТИКЕР:              {escape(str(item.get('spot_ticker') or '—'))}",
                    f"SPOT ЦЕНА:          {_number(item.get('spot_price'), 4)}",
                    f"SPOT СРЕДНИЙ ₽×V:   {_money(item.get('spot_average_daily_money'))}",
                    f"SPOT СЕССИЯ ₽×V:    {_money(item.get('spot_money_volume'))}",
                    f"SPOT ₽×V/МИН:       {_money(item.get('spot_money_per_minute'))}",
                    f"ИЗМЕНЕНИЕ SPOT:     {_number(item.get('spot_change_percent'), 2)}%",
                    f"RS:                 {_number(item.get('relative_strength'), 3)} п.п.",
                    f"RS SCORE:           {_number(item.get('relative_strength_score'), 1)} / 100",
                    "",
                    f"ЛОКАЛЬНЫЙ МАКСИМУМ: {_number(item.get('previous_high'), 4)}",
                    f"ЛОКАЛЬНЫЙ МИНИМУМ:  {_number(item.get('previous_low'), 4)}",
                    f"ТРИГГЕР УРОВНЯ:     {_number(item.get('entry_trigger'), 4)}",
                    f"ТРИГГЕР:            {'АКТИВЕН' if trigger_active else 'ОЖИДАЕТ'}",
                    f"ТРИГГЕР УРОВЕНЬ:    {'ЕСТЬ' if trigger_present else 'НЕТ'}",
                    f"SPOT ГОТОВ:         {'ДА' if signal_state_raw == 'READY' else 'НЕТ'}",
                    f"SPOT ПОДТВЕРЖДЁН:   {'ДА' if signal_state_raw == 'CONFIRMED' else 'НЕТ'}",
                    "",
                    "ФЬЮЧЕРС:            ТОЛЬКО СОПОСТАВЛЕНИЕ ПОСЛЕ SPOT-ГОТОВНОСТИ",
                    "ФЬЮЧЕРС ИЗ СИГНАЛА:  НЕ ИСПОЛЬЗУЕТСЯ",
                    "ФЬЮЧЕРС В РЕЙТИНГЕ: НЕТ",
                    f"ПРИЧИНА:             {escape(_signal_reason(item.get('signal_state_reason')))}",
                    "",
                    "─" * 86,
                ])

        if diagnostics:
            lines.extend([
                "",
                "ДИАГНОСТИКА ОТБОРА:",
                f"ALL_TQBR={diagnostics.get('stock_universe_total', 0)}  "
                f"MONEY_SCREENED={diagnostics.get('stock_money_screened', 0)}  "
                f"DEEP={diagnostics.get('stock_deep_analyzed', 0)}  "
                f"MONEY_LEADERS={diagnostics.get('money_leader_count', 0)}  "
                f"ACCEPTED={diagnostics.get('candidate_accepted', 0)}  "
                f"REJECTED={diagnostics.get('candidate_rejected', 0)}  "
                f"SPOT={diagnostics.get('spot_candidates', 0)}  "
                f"MACRO_WATCH={diagnostics.get('macro_candidates', 0)}  "
                f"SELECTED_SPOT={diagnostics.get('selected', 0)}  "
                f"READY={diagnostics.get('ready', 0)}  "
                f"CONFIRMED={diagnostics.get('confirmed', 0)}  "
                f"WATCH={diagnostics.get('watch', 0)}  "
                f"WAIT={diagnostics.get('wait', 0)}",
            ])
            rejections = diagnostics.get("candidate_rejections", {}) or {}
            if rejections:
                lines.append("ПРИЧИНЫ ОТКЛОНЕНИЯ: " + "; ".join(
                    f"{_rejection_reason(key)}={value}" for key, value in sorted(rejections.items())
                ))

        lines.extend([
            "",
            "ЦЕПОЧКА: ALL TQBR → MONEY-FIRST → TOP ACTIVE → SPOT DIRECTION → RS → SETUP → TRIGGER → READINESS",
            "",
            "TOP ACTIVE MONEY показывает текущую активность и не является торговым сигналом.",
            "Для акций направление, деньги, RS, сетап, триггер и готовность определяются только по SPOT.",
            "MACRO/FUTURES DIRECT показывается отдельным наблюдательным слоем и не входит в SPOT-рейтинг.",
            "Фьючерс для SPOT-кандидата — только справочное сопоставление; пользователь самостоятельно выбирает контракт.",
            "ОЦЕНКА ВОЗМОЖНОСТИ — детерминированный рейтинг радарной модели, а не статистическая вероятность исхода.",
            "Пользователь самостоятельно выбирает фьючерс, график, точку входа и риск.",
            "Это информационный радар: исполнение ордеров, стоп-лосс, тейк-профит и расчёт позиции отсутствуют.",
            "═" * 86,
            "</pre>",
        ])
        self.result_box.setHtml("\n".join(lines))
