"""Trader_7_12 Pro — canonical SPOT + macro opportunity watchlist UI."""

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


def _signal_reason(value):
    text = str(value or "—")
    return REASON_LABELS.get(text, text)


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


def _action_label(signal_state, trigger_active, is_macro=False):
    state = str(signal_state or "WAIT").upper()
    if is_macro and state not in {"READY", "CONFIRMED"}:
        return "НАБЛЮДАТЬ — MACRO/FUTURES PROXY, SPOT-СИГНАЛ НЕ СФОРМИРОВАН"
    if state == "CONFIRMED":
        return "СЦЕНАРИЙ ПОДТВЕРЖДЁН — РЕШЕНИЕ О ВХОДЕ ПРИНИМАЕТ ПОЛЬЗОВАТЕЛЬ"
    if state == "READY":
        return "СЦЕНАРИЙ ГОТОВ — ПРОВЕРИТЬ ТОЧКУ ВХОДА И РИСК"
    if trigger_active:
        return "НАБЛЮДАТЬ — ТРИГГЕР ЕСТЬ, НО НУЖНА СТАБИЛЬНОСТЬ"
    return "ЖДАТЬ — ТРИГГЕР НЕ АКТИВЕН"


class WatchlistTraderWindow(TraderWindow):
    """Read-only GUI bound to the SPOT-first watchlist contract."""

    VERSION = "1.7"

    def __init__(self, scanner_enabled=True):
        super().__init__(scanner_enabled=scanner_enabled)
        self.setWindowTitle("Trader_7_12 Pro — радар возможностей")
        self.subtitle.setText("SPOT • MACRO • НАПРАВЛЕНИЕ • ДЕНЬГИ • RS • СЕТАП • ТРИГГЕР • ГОТОВНОСТЬ")

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

        # The money-first screen is always useful, even when no instrument has
        # yet passed the expensive direction/setup/readiness stage. It is shown
        # as discovery data, never as a trade signal.
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

        if not results:
            lines.extend([
                "",
                "НЕТ КАНДИДАТОВ В СПИСКЕ НАБЛЮДЕНИЯ",
                "",
                "В текущей сессии нет SPOT-активов, прошедших обязательные проверки отбора.",
                "Но TOP ACTIVE MONEY выше показывает, где сейчас находится основная активность.",
            ])
        else:
            for idx, item in enumerate(results, start=1):
                is_macro = str(item.get("analysis_source") or "SPOT").upper() == "FUTURES_DIRECT"
                source_label = "MACRO / FUTURES DIRECT" if is_macro else "SPOT / TQBR"
                direction = _label(DIRECTION_LABELS, item.get("direction"))
                setup = _label(SETUP_LABELS, item.get("setup"))
                setup_state = _label(SETUP_STATE_LABELS, item.get("setup_state"))
                signal_state_raw = str(item.get("signal_state") or "WAIT").upper()
                signal_state = SIGNAL_STATE_LABELS.get(signal_state_raw, "ОЖИДАНИЕ")
                rs = _rs_label(item)
                opportunity = item.get("opportunity_score", item.get("session_rank_score", 0))
                trigger_present = bool(item.get("trigger_present"))
                trigger_active = bool(item.get("trigger_active"))
                if is_macro:
                    activity_label = "НЕТ SPOT-ДАННЫХ — FUTURES PROXY"
                    price_label = "MACRO ЦЕНА"
                    average_label = "MACRO СРЕДНИЙ ₽×V"
                    session_label = "MACRO СЕССИЯ ₽×V"
                    pace_label = "MACRO ₽×V/МИН"
                    change_label = "ИЗМЕНЕНИЕ MACRO"
                else:
                    activity_label = _activity_label(item)
                    price_label = "SPOT ЦЕНА"
                    average_label = "SPOT СРЕДНИЙ ₽×V"
                    session_label = "SPOT СЕССИЯ ₽×V"
                    pace_label = "SPOT ₽×V/МИН"
                    change_label = "ИЗМЕНЕНИЕ SPOT"

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
                    f"РЕКОМЕНДАЦИЯ:       {_action_label(signal_state_raw, trigger_active, is_macro)}",
                    "",
                    f"ТИКЕР:              {escape(str(item.get('spot_ticker') or '—'))}",
                    f"{price_label}:          {_number(item.get('spot_price'), 4)}",
                    f"{average_label}:   {_money(item.get('spot_average_daily_money'))}",
                    f"{session_label}:    {_money(item.get('spot_money_volume'))}",
                    f"{pace_label}:       {_money(item.get('spot_money_per_minute'))}",
                    f"{change_label}:     {_number(item.get('spot_change_percent'), 2)}%",
                    f"RS:                 {_number(item.get('relative_strength'), 3)} п.п.",
                    f"RS SCORE:           {_number(item.get('relative_strength_score'), 1)} / 100",
                    "",
                    f"ЛОКАЛЬНЫЙ МАКСИМУМ: {_number(item.get('previous_high'), 4)}",
                    f"ЛОКАЛЬНЫЙ МИНИМУМ:  {_number(item.get('previous_low'), 4)}",
                    f"ТРИГГЕР УРОВНЯ:     {_number(item.get('entry_trigger'), 4)}",
                    f"ТРИГГЕР:            {'АКТИВЕН' if trigger_active else 'ОЖИДАЕТ'}",
                    f"ТРИГГЕР УРОВЕНЬ:    {'ЕСТЬ' if trigger_present else 'НЕТ'}",
                    f"SPOT ГОТОВ:         {'НЕТ — MACRO PROXY' if is_macro else ('ДА' if signal_state_raw == 'READY' else 'НЕТ')}",
                    f"SPOT ПОДТВЕРЖДЁН:   {'НЕТ — MACRO PROXY' if is_macro else ('ДА' if signal_state_raw == 'CONFIRMED' else 'НЕТ')}",
                    "",
                    "ФЬЮЧЕРС:            ТОЛЬКО СОПОСТАВЛЕНИЕ" if not is_macro else "ФЬЮЧЕРС:            ИСТОЧНИК MACRO PROXY",
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
                f"SPOT={diagnostics.get('spot_candidates', diagnostics.get('radar_results', 0))}  "
                f"MACRO={diagnostics.get('macro_candidates', 0)}  "
                f"ОТОБРАНО={diagnostics.get('selected', 0)}  "
                f"ГОТОВ={diagnostics.get('ready', 0)}  "
                f"ПОДТВЕРЖДЁН={diagnostics.get('confirmed', 0)}  "
                f"НАБЛЮДЕНИЕ={diagnostics.get('watch', 0)}  "
                f"ОЖИДАНИЕ={diagnostics.get('wait', 0)}",
            ])

        lines.extend([
            "",
            "ЦЕПОЧКА: ALL TQBR → MONEY-FIRST → TOP ACTIVE → SPOT DIRECTION → RS → SETUP → TRIGGER → READINESS",
            "",
            "TOP ACTIVE MONEY показывает текущую активность и не является торговым сигналом.",
            "Для акций направление, деньги, RS, сетап, триггер и готовность определяются только по SPOT.",
            "MACRO/FUTURES DIRECT показывается отдельно и не выдаётся за SPOT-данные.",
            "Фьючерсы для SPOT-кандидата — только справочное сопоставление после SPOT-readiness.",
            "ОЦЕНКА ВОЗМОЖНОСТИ — детерминированный рейтинг радарной модели, а не статистическая вероятность исхода.",
            "Пользователь самостоятельно выбирает фьючерс, график, точку входа и риск.",
            "Это информационный радар: исполнение ордеров, стоп-лосс, тейк-профит и расчёт позиции отсутствуют.",
            "═" * 86,
            "</pre>",
        ])
        self.result_box.setHtml("\n".join(lines))
