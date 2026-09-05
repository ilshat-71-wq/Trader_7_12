"""Trader_7_12 Pro — professional read-only market-attention dashboard."""

from html import escape

from PySide6.QtCore import QThread

from ui import TraderWindow, MarketScanWorker


def _num(value, digits=2):
    try:
        return f"{float(value):,.{digits}f}".replace(",", " ")
    except (TypeError, ValueError):
        return "—"


def _money(value):
    try:
        value = float(value or 0)
    except (TypeError, ValueError):
        return "—"
    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f} млрд ₽"
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f} млн ₽"
    return f"{value:,.0f} ₽".replace(",", " ")


class WatchlistTraderWindow(TraderWindow):
    VERSION = "2.2.2"

    def __init__(self, scanner_enabled=True):
        super().__init__(scanner_enabled=scanner_enabled)
        self.setWindowTitle("Trader_7_12 Pro — Market Attention Radar")
        self.subtitle.setText("MARKET ATTENTION • MONEY FLOW • RS • CURRENT SESSION • READ-ONLY")
        self.result_box.setStyleSheet("font-size:15px;")

    def run_market_scan(self):
        if not self.scanner_enabled:
            self.result_box.setText("БКС недоступен. Сканирование временно отключено.")
            return
        if self.scan_thread is not None and self.scan_thread.isRunning():
            return
        self.scan_button.setEnabled(False)
        self._start_scan_animation()
        try:
            if self.scanner is None:
                from services.market_attention_scanner_service import MarketAttentionScannerService
                self.scanner = MarketAttentionScannerService()
            self.scan_thread = QThread(self)
            self.scan_worker = MarketScanWorker(self.scanner, limit=3)
            self.scan_worker.moveToThread(self.scan_thread)
            self.scan_thread.started.connect(self.scan_worker.run)
            self.scan_worker.finished.connect(self._scan_finished)
            self.scan_worker.failed.connect(self._scan_failed)
            self.scan_worker.finished.connect(self.scan_thread.quit)
            self.scan_worker.failed.connect(self.scan_thread.quit)
            self.scan_thread.finished.connect(self._scan_thread_finished)
            self.scan_thread.start()
        except Exception as exc:
            self._scan_failed(f"{type(exc).__name__}: {exc}")

    def _card(self, item, role):
        long_side = role == "LONG_CANDIDATE"
        accent = "#8fd694" if long_side else "#e58b8b"
        label = "LONG" if long_side else "SHORT"
        relation = escape(str(item.get("market_relation") or "—"))
        ticker = escape(str(item.get("spot_ticker") or "—"))
        rs = item.get("relative_strength")
        rs_text = "—" if rs is None else f"{float(rs):+.2f} п.п."
        return f"""
        <div style="border:1px solid #394149;border-radius:14px;padding:18px;margin:10px 0;background:#171b20;">
          <div style="font-size:15px;color:{accent};font-weight:800;letter-spacing:1px;">{label} CANDIDATE</div>
          <div style="font-size:32px;font-weight:900;margin-top:3px;">{ticker}</div>
          <div style="color:#9fa8b1;margin:2px 0 14px;">{escape(str(item.get('market_group') or '—'))} • {relation}</div>
          <table width="100%" cellspacing="0" cellpadding="3">
            <tr><td><b>Цена</b></td><td align="right">{_num(item.get('price'),4)}</td><td><b>Изменение</b></td><td align="right" style="color:{accent};font-weight:800;">{_num(item.get('change_percent'),2)}%</td></tr>
            <tr><td><b>RS</b></td><td align="right">{rs_text}</td><td><b>ATTENTION</b></td><td align="right" style="font-weight:800;">{_num(item.get('attention_score'),1)}/100</td></tr>
            <tr><td><b>₽×V сессии</b></td><td align="right">{_money(item.get('session_money'))}</td><td><b>₽×V/мин</b></td><td align="right">{_money(item.get('recent_money_per_minute'))}</td></tr>
            <tr><td><b>Ускорение потока</b></td><td align="right">{_num(item.get('money_acceleration'),1)}%</td><td><b>Источник</b></td><td align="right">BASE / SPOT</td></tr>
          </table>
        </div>"""

    def _scan_finished(self, results):
        self.scan_button.setEnabled(True)
        self._stop_scan_animation()
        info = self.session_service.get_session_info()
        diagnostics = getattr(self.scanner, "_last_scan_diagnostics", {}) or {}
        results = results or []
        status = str(diagnostics.get("status") or "").upper()

        benchmark = diagnostics.get("benchmark") or "—"
        change = diagnostics.get("benchmark_change_percent")
        market_text = "—" if change is None else f"{benchmark} {float(change):+.2f}%"
        long_item = next((x for x in results if x.get("selection_role") == "LONG_CANDIDATE"), None)
        short_item = next((x for x in results if x.get("selection_role") == "SHORT_CANDIDATE"), None)
        watch = [x for x in results if x not in (long_item, short_item)]
        html = [
            "<div style='font-family:\"Helvetica Neue\",Arial;color:#e6e9ed;'>",
            f"<div style='font-size:12px;color:#89939d;letter-spacing:1px;'>TRADER_7_12 PRO v{self.VERSION} • {info.get('date','—')} • МСК {info.get('time','—')}</div>",
            f"<div style='font-size:22px;font-weight:800;margin-top:5px;'>{info.get('label','РЫНОК')}</div>",
            f"<div style='font-size:14px;color:#aab2b9;margin:4px 0 14px;'>MARKET BENCHMARK: <b>{escape(market_text)}</b> • текущая сессия</div>",
        ]
        if status == "BENCHMARK_UNAVAILABLE":
            html.append("<div style='padding:18px;border:1px solid #394149;border-radius:12px;background:#171b20;'>Benchmark недоступен. LONG/SHORT не формируются до восстановления валидного рыночного benchmark.</div>")
        elif status == "INSUFFICIENT_COVERAGE":
            html.append(
                "<div style='padding:18px;border:1px solid #6f5d3b;border-radius:12px;background:#211d17;'>"
                f"Покрытие текущего скана недостаточно для честного LONG/SHORT отбора: <b>{_num(diagnostics.get('coverage_percent'),1)}%</b> "
                f"при минимуме <b>{_num(diagnostics.get('coverage_required_percent'),1)}%</b>. "
                "Направленные кандидаты намеренно не публикуются."
                "</div>"
            )
        elif long_item:
            html.append(self._card(long_item, "LONG_CANDIDATE"))
        if short_item:
            html.append(self._card(short_item, "SHORT_CANDIDATE"))
        if watch:
            html.append("<div style='font-size:14px;font-weight:800;margin:16px 0 7px;color:#aab57d;'>ЕЩЁ В ПОЛЕ ЗРЕНИЯ</div>")
            html.append("<table width='100%' cellspacing='0' cellpadding='7' style='background:#171b20;border:1px solid #394149;'><tr style='color:#89939d;'><th align='left'>Актив</th><th>Изм.</th><th>RS</th><th>₽×V/мин</th><th>Attention</th></tr>")
            for item in watch:
                rs = item.get("relative_strength")
                rs_text = "—" if rs is None else f"{float(rs):+.2f}"
                html.append(f"<tr><td><b>{escape(str(item.get('spot_ticker') or '—'))}</b></td><td align='right'>{_num(item.get('change_percent'),2)}%</td><td align='right'>{rs_text}</td><td align='right'>{_money(item.get('recent_money_per_minute'))}</td><td align='right'>{_num(item.get('attention_score'),1)}</td></tr>")
            html.append("</table>")
        if status not in {"BENCHMARK_UNAVAILABLE"} and not long_item and not short_item:
            html.append("<div style='padding:18px;border:1px solid #394149;border-radius:12px;background:#171b20;'>Нет достаточных свежих данных для честного LONG/SHORT отбора. Сканер не подменяет отсутствующие данные фьючерсами.</div>")
        preferred = diagnostics.get("preferred_window_active")
        preferred_text = "активно" if preferred else "вне предпочтительного окна"
        html.extend([
            "<div style='margin-top:16px;color:#89939d;font-size:12px;'>",
            f"UNIVERSE {diagnostics.get('universe_total',0)} • ANALYZED {diagnostics.get('analyzed',0)} • STOCKS {diagnostics.get('stocks_total',0)}",
            f"<br>Покрытие: {float(diagnostics.get('coverage_percent', 0) or 0):.1f}%"
            + (f" • пропущено {diagnostics.get('skipped_total',0)}" if diagnostics.get('skipped_total') is not None else ""),
            f"<br>Предпочтительное окно 09:50–13:00 MSK: {preferred_text}.",
            "<br>Сканер работает весь период текущей торговой сессии; предпочтительное окно не ограничивает его работу.",
            "<br>Сильнее рынка → LONG; слабее рынка → SHORT.",
            "<br>Сканер только анализирует рынок. Исполнение сделок и выбор инструмента остаются за пользователем.",
            "</div></div>",
        ])
        self.result_box.setHtml("".join(html))
