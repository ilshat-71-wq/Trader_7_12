"""Trader_7_12 Pro — canonical SPOT opportunity watchlist UI.

This module keeps the existing scan window/animation from ui.py but replaces
only the result renderer so the GUI follows the canonical TOP-2/3 watchlist
architecture from MorningTradingPipelineService.
"""

from html import escape

from ui import (
    TraderWindow,
    DIRECTION_LABELS,
    SETUP_LABELS,
    SETUP_STATE_LABELS,
    RS_LABELS,
    SESSION_LABELS,
    _label,
    _money,
    _number,
    _rs_label,
    _activity_label,
)


class WatchlistTraderWindow(TraderWindow):
    """Read-only GUI bound to the SPOT opportunity watchlist contract."""

    VERSION = "1.0"

    def __init__(self, scanner_enabled=True):
        super().__init__(scanner_enabled=scanner_enabled)
        self.setWindowTitle("Trader_7_12 Pro — SPOT opportunity watchlist")
        self.subtitle.setText("SPOT • OPPORTUNITY • RS • SETUP STATE • ACTIVITY")

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
            "TRADER_7_12 PRO — SPOT OPPORTUNITY WATCHLIST",
            "═" * 86,
            "",
            f"{session_name} • {info.get('date','—')} • МСК {info.get('time','—')}",
            "",
            "ГДЕ ДЕНЬГИ • ГДЕ СИЛА/СЛАБОСТЬ • ГДЕ ЕСТЬ ПОТЕНЦИАЛ ДВИЖЕНИЯ",
            "",
        ]

        if not results:
            lines.extend([
                "NO WATCHLIST CANDIDATES",
                "",
                "В текущей сессии нет SPOT-активов, прошедших обязательные eligibility-проверки.",
            ])
        else:
            for idx, item in enumerate(results, start=1):
                direction = _label(DIRECTION_LABELS, item.get("direction"))
                setup = _label(SETUP_LABELS, item.get("setup"))
                state = _label(SETUP_STATE_LABELS, item.get("setup_state"))
                rs = _rs_label(item)
                opportunity = item.get("opportunity_score", item.get("session_rank_score", 0))
                lines.extend([
                    "",
                    f"████  #{idx}  {escape(str(item.get('spot_ticker') or '—'))}  ████",
                    f"НАПРАВЛЕНИЕ:       {direction}",
                    f"OPPORTUNITY:        {_number(opportunity, 1)} / 100",
                    f"СЕССИОННАЯ ОЦЕНКА: {_number(item.get('session_rank_score'), 1)} / 100",
                    f"RS:                 {rs}",
                    f"АКТИВНОСТЬ SPOT:   {_activity_label(item)}",
                    f"СЕТАП:              {setup}",
                    f"СОСТОЯНИЕ:          {state}",
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
                    "",
                    "─" * 86,
                ])

        if diagnostics:
            lines.extend([
                "",
                "FILTER DIAGNOSTICS:",
                f"RADAR={diagnostics.get('radar_results', 0)}  "
                f"CANDIDATES={diagnostics.get('candidates', 0)}  "
                f"READY={diagnostics.get('ready', 0)}  "
                f"CONFIRMED={diagnostics.get('confirmed', 0)}  "
                f"WATCH={diagnostics.get('watch', 0)}  "
                f"WAIT={diagnostics.get('wait', 0)}  "
                f"SELECTED={diagnostics.get('selected', 0)}",
            ])

        lines.extend([
            "",
            "СТРАТЕГИЯ: ПРОДОЛЖЕНИЕ / СИЛА-СЛАБОСТЬ / АКТИВНОСТЬ",
            "",
            "TOP-2/3 — WATCHLIST ВОЗМОЖНОСТЕЙ, А НЕ ГОТОВЫЕ ВХОДЫ.",
            "WAIT/WATCH могут оставаться в TOP, если SPOT проходит обязательные eligibility-проверки.",
            "Фьючерс не подтверждает идею, не влияет на RS/ranking и выбирается пользователем отдельно.",
            "Это read-only SPOT-радар: position sizing, SL/TP и исполнение ордеров отсутствуют.",
            "═" * 86,
            "</pre>",
        ])
        self.result_box.setHtml("\n".join(lines))
