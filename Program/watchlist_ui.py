"""Trader_7_12 Pro — canonical SPOT opportunity watchlist UI."""

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

    VERSION = "1.5"

    def __init__(self, scanner_enabled=True):
        super().__init__(scanner_enabled=scanner_enabled)
        self.setWindowTitle("Trader_7_12 Pro — SPOT-радар возможностей")
        self.subtitle.setText("SPOT • НАПРАВЛЕНИЕ • ДЕНЬГИ • RS • СЕТАП • ТРИГГЕР • ГОТОВНОСТЬ")

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
            "TRADER_7_12 PRO — SPOT-РАДАР ВОЗМОЖНОСТЕЙ",
            "═" * 86,
            "",
            f"{session_name} • {info.get('date','—')} • МСК {info.get('time','—')}",
            "",
            "ГДЕ ДЕНЬГИ • ГДЕ СИЛА/СЛАБОСТЬ • ГДЕ СФОРМИРОВАЛСЯ SPOT-СЦЕНАРИЙ",
            "",
        ]

        if not results:
            lines.extend([
                "НЕТ КАНДИДАТОВ В СПИСКЕ НАБЛЮДЕНИЯ",
                "",
                "В текущей сессии нет SPOT-активов, прошедших обязательные проверки отбора.",
            ])
        else:
            for idx, item in enumerate(results, start=1):
                direction = _label(DIRECTION_LABELS, item.get("direction"))
                setup = _label(SETUP_LABELS, item.get("setup"))
                setup_state = _label(SETUP_STATE_LABELS, item.get("setup_state"))
                signal_state_raw = str(item.get("signal_state") or "WAIT").upper()
                signal_state = SIGNAL_STATE_LABELS.get(signal_state_raw, "ОЖИДАНИЕ")
                rs = _rs_label(item)
                opportunity = item.get("opportunity_score", item.get("session_rank_score", 0))
                trigger_present = bool(item.get("trigger_present"))
                trigger_active = bool(item.get("trigger_active"))
                lines.extend([
                    "",
                    f"████  #{idx}  {escape(str(item.get('spot_ticker') or '—'))}  ████",
                    f"НАПРАВЛЕНИЕ:       {direction}",
                    f"ОЦЕНКА ВОЗМОЖНОСТИ: {_number(opportunity, 1)} / 100",
                    f"СИЛА СЦЕНАРИЯ:     {_scenario_grade(opportunity)}",
                    f"ОЦЕНКА СЕССИИ:     {_number(item.get('session_rank_score'), 1)} / 100",
                    f"RS:                 {rs}",
                    f"АКТИВНОСТЬ SPOT:    {_activity_label(item)}",
                    f"СЕТАП:              {setup}",
                    f"СОСТОЯНИЕ СЕТАПА:   {setup_state}",
                    f"СОСТОЯНИЕ СИГНАЛА:  {signal_state}",
                    f"РЕКОМЕНДАЦИЯ:       {_action_label(signal_state_raw, trigger_active)}",
                    "",
                    f"SPOT ТИКЕР:         {escape(str(item.get('spot_ticker') or '—'))}",
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
                    "ФЬЮЧЕРС:            ТОЛЬКО СОПОСТАВЛЕНИЕ",
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
                f"РАДАР={diagnostics.get('radar_results', 0)}  "
                f"КАНДИДАТЫ={diagnostics.get('candidates', 0)}  "
                f"ОТОБРАНО={diagnostics.get('selected', 0)}  "
                f"ГОТОВ={diagnostics.get('ready', 0)}  "
                f"ПОДТВЕРЖДЁН={diagnostics.get('confirmed', 0)}  "
                f"НАБЛЮДЕНИЕ={diagnostics.get('watch', 0)}  "
                f"ОЖИДАНИЕ={diagnostics.get('wait', 0)}",
            ])

        lines.extend([
            "",
            "ЦЕПОЧКА: НАПРАВЛЕНИЕ → СЕТАП → ТРИГГЕР → ГОТОВНОСТЬ/ПОДТВЕРЖДЕНИЕ → ФЬЮЧЕРСЫ",
            "",
            "НАПРАВЛЕНИЕ определяется только по SPOT.",
            "ДЕНЬГИ и АКТИВНОСТЬ — по реальному SPOT-обороту и ₽×V/мин относительно нормы.",
            "RS — относительная сила/слабость к рыночному benchmark.",
            "СЕТАП и ТРИГГЕР определяются только по SPOT-структуре и уровням.",
            "ГОТОВ = SPOT-сетап сформирован, триггер активирован и пройдена проверка стабильности.",
            "ПОДТВЕРЖДЁН = SPOT-сценарий подтверждён собственной SPOT-структурой.",
            "Фьючерсы — только справочное сопоставление; они не подтверждают и не блокируют SPOT.",
            "ОЦЕНКА ВОЗМОЖНОСТИ — детерминированный рейтинг радарной модели, а не статистическая вероятность исхода.",
            "Для реальной вероятности нужна отдельная историческая калибровка результатов по будущему движению.",
            "Пользователь самостоятельно выбирает фьючерс, график, точку входа и риск.",
            "Это информационный радар: исполнение ордеров, стоп-лосс, тейк-профит и расчёт позиции отсутствуют.",
            "═" * 86,
            "</pre>",
        ])
        self.result_box.setHtml("\n".join(lines))
