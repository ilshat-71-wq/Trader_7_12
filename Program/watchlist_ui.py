"""Trader_7_12 Pro — canonical SPOT opportunity watchlist UI.

The GUI exposes the complete read-only signal chain:
SPOT direction -> SPOT setup -> trigger -> READY -> futures confirmation -> CONFIRMED.
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


SIGNAL_STATE_LABELS = {
    "WAIT": "ОЖИДАНИЕ",
    "READY": "ГОТОВ — ЖДЁМ ПОДТВЕРЖДЕНИЕ",
    "CONFIRMED": "ПОДТВЕРЖДЁН",
    "BLOCKED": "ЗАБЛОКИРОВАН",
}


class WatchlistTraderWindow(TraderWindow):
    """Read-only GUI bound to the SPOT opportunity watchlist contract."""

    VERSION = "1.1"

    def __init__(self, scanner_enabled=True):
        super().__init__(scanner_enabled=scanner_enabled)
        self.setWindowTitle("Trader_7_12 Pro — SPOT opportunity watchlist")
        self.subtitle.setText("SPOT • DIRECTION • SETUP • TRIGGER • FUTURES CONFIRMATION")

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
            "TRADER_7_12 PRO — SPOT SIGNAL WATCHLIST",
            "═" * 86,
            "",
            f"{session_name} • {info.get('date','—')} • МСК {info.get('time','—')}",
            "",
            "ГДЕ ДЕНЬГИ • ГДЕ СИЛА/СЛАБОСТЬ • ГДЕ СФОРМИРОВАЛСЯ СИГНАЛ",
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
                setup_state = _label(SETUP_STATE_LABELS, item.get("setup_state"))
                signal_state = SIGNAL_STATE_LABELS.get(str(item.get("signal_state") or "WAIT").upper(), str(item.get("signal_state") or "ОЖИДАНИЕ"))
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
                    f"SETUP STATE:        {setup_state}",
                    f"СОСТОЯНИЕ СИГНАЛА: {signal_state}",
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
                    f"ТРИГГЕР АКТИВЕН:    {'ДА' if float(item.get('entry_trigger', 0) or 0) > 0 else 'НЕТ'}",
                    "",
                    f"FUTURES:             {escape(str(item.get('futures_ticker') or '—'))}",
                    f"FUTURES CONFIRM:     {escape(str(item.get('futures_confirmation') or 'NOT_CHECKED'))}",
                    f"FUTURES STATUS:      {escape(str(item.get('futures_confirmation_status') or 'NOT_CHECKED'))}",
                    f"FUTURES SCORE:       {_number(item.get('futures_confirmation_score'), 0)} / 100",
                    f"FUTURES TRADES:      {_number(item.get('futures_trade_count'), 0)}",
                    f"FUTURES ₽×V:         {_money(item.get('futures_money_volume'))}",
                    f"FUTURES Δ:           {_number(item.get('futures_price_change_percent'), 2)}%",
                    f"ПРИЧИНА:             {escape(str(item.get('futures_confirmation_reason') or item.get('signal_state_reason') or '—'))}",
                    "",
                    "─" * 86,
                ])

        if diagnostics:
            lines.extend([
                "",
                "FILTER DIAGNOSTICS:",
                f"RADAR={diagnostics.get('radar_results', 0)}  "
                f"CANDIDATES={diagnostics.get('candidates', 0)}  "
                f"SELECTED={diagnostics.get('selected', 0)}  "
                f"READY={diagnostics.get('ready', 0)}  "
                f"CONFIRMED={diagnostics.get('confirmed', 0)}  "
                f"BLOCKED={diagnostics.get('blocked', 0)}  "
                f"WATCH={diagnostics.get('watch', 0)}  "
                f"WAIT={diagnostics.get('wait', 0)}",
            ])

        lines.extend([
            "",
            "ЦЕПОЧКА: DIRECTION → SETUP → TRIGGER → READY → FUTURES → CONFIRMED",
            "",
            "DIRECTION определяется только по SPOT.",
            "SETUP и TRIGGER определяются только по SPOT-структуре.",
            "READY = SPOT-сетап сформирован и есть реальный trigger.",
            "CONFIRMED = READY + выбранный фьючерс подтверждает то же направление.",
            "Фьючерс не может изменить направление, setup или trigger.",
            "Это read-only радар: исполнение ордеров, SL/TP и position sizing отсутствуют.",
            "═" * 86,
            "</pre>",
        ])
        self.result_box.setHtml("\n".join(lines))
