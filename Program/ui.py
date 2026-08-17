"""Trader_7_12 Pro — professional, compact, session-aware scanner UI."""

from html import escape
from PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget
from services.market_session_service import MarketSessionService

DIRECTION_LABELS={"LONG":"ЛОНГ","SHORT":"ШОРТ"}
SETUP_LABELS={"BREAKOUT":"ПРОБОЙ","PULLBACK":"ОТКАТ","REBOUND":"ОТСКОК","FIRST_PULLBACK":"ПЕРВЫЙ ОТКАТ","FIRST_REBOUND":"ПЕРВЫЙ ОТСКОК"}
SETUP_STATE_LABELS={"READY":"ГОТОВ","WATCH":"НАБЛЮДЕНИЕ","CONFIRMED":"ПОДТВЕРЖДЁН","WAIT":"ОЖИДАНИЕ"}
RS_LABELS={"STRONGER":"СИЛЬНЕЕ РЫНКА","WEAKER":"СЛАБЕЕ РЫНКА","NEUTRAL":"НЕЙТРАЛЬНО","UNAVAILABLE":"RS НЕДОСТУПЕН"}
SESSION_LABELS={"PRE_OPEN":"ПРЕ-ОТКРЫТИЕ","MORNING":"УТРЕННЯЯ СЕССИЯ","MAIN":"ОСНОВНАЯ СЕССИЯ","EVENING":"ВЕЧЕРНЯЯ СЕССИЯ","CLOSED":"РЫНОК ЗАКРЫТ"}
LONG_COLOR="#8fd694"
SHORT_COLOR="#e58b8b"
ACCENT_COLOR="#b7d96b"


def _label(mapping,value): return mapping.get(str(value or "-").upper(),value or "-")
def _money(value):
    try:return f"{float(value or 0):,.0f} ₽".replace(","," ")
    except (TypeError,ValueError):return "—"
def _number(value,digits=2):
    try:return f"{float(value or 0):,.{digits}f}".replace(","," ")
    except (TypeError,ValueError):return "—"
def _rs_label(item):
    if str(item.get("relative_strength_status") or "").upper() not in {"OK","AVAILABLE"}: return RS_LABELS["UNAVAILABLE"]
    return RS_LABELS.get(str(item.get("relative_strength_signal") or "NEUTRAL").upper(),"НЕЙТРАЛЬНО")
def _activity_label(item):
    r=float(item.get("spot_money_ratio",0) or 0)
    return "ОЧЕНЬ ВЫСОКАЯ" if r>=3 else "ВЫСОКАЯ" if r>=1.5 else "НОРМАЛЬНАЯ" if r>=.75 else "НИЖЕ НОРМЫ" if r>0 else "НЕТ ДАННЫХ"


class MarketScanWorker(QObject):
    finished=Signal(object); failed=Signal(str)
    def __init__(self,scanner,limit=3): super().__init__(); self.scanner=scanner; self.limit=limit
    def run(self):
        try:self.finished.emit(self.scanner.scan(limit=self.limit))
        except Exception as exc:self.failed.emit(f"{type(exc).__name__}: {exc}")


class TraderWindow(QWidget):
    """Read-only professional radar with live Moscow time."""
    def __init__(self,scanner_enabled=True):
        super().__init__(); self.setWindowTitle("Trader_7_12 Pro — Рыночный радар"); self.resize(1120,780)
        self.scanner=None; self.scanner_enabled=scanner_enabled; self.scan_thread=None; self.scan_worker=None
        self.session_service=MarketSessionService(); self.animation_step=0
        self.clock_timer=QTimer(self); self.clock_timer.timeout.connect(self._update_session_header)
        self.scan_animation_timer=QTimer(self); self.scan_animation_timer.timeout.connect(self._animate_scan)
        self.init_ui(); self.clock_timer.start(1000); self._update_session_header()

    def init_ui(self):
        self.setStyleSheet("""
        QWidget{background:#20252b;color:#e6e9ed;font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Helvetica Neue",Arial}
        QLabel{color:#e6e9ed}
        QPushButton{background:#30373f;color:#f0f2f4;border:1px solid #46505a;border-radius:8px;padding:10px 18px}
        QPushButton:hover{background:#38414a}
        QPushButton:disabled{color:#c9d38b;background:#30372e;border:1px solid #59634a}
        QTextEdit{background:#171b20;color:#dfe3e7;border:1px solid #394149;border-radius:8px;padding:14px}
        """)
        self.title=QLabel("TRADER_7_12 PRO"); self.title.setAlignment(Qt.AlignCenter); self.title.setStyleSheet("font-size:29px;font-weight:800;letter-spacing:1px;padding:8px")
        self.subtitle=QLabel(); self.subtitle.setAlignment(Qt.AlignCenter); self.subtitle.setStyleSheet("font-size:14px;color:#9fa8b1;padding:2px")
        self.session_label=QLabel(); self.session_label.setAlignment(Qt.AlignCenter); self.session_label.setStyleSheet("font-size:20px;font-weight:700;color:#cbd1d7;padding:5px")
        self.clock_label=QLabel(); self.clock_label.setAlignment(Qt.AlignCenter); self.clock_label.setStyleSheet("font-size:14px;color:#9fa8b1;padding-bottom:5px")
        self.scan_button=QPushButton("●  СКАНИРОВАТЬ РЫНОК"); self.scan_button.setMinimumHeight(54); self.scan_button.setStyleSheet("font-size:18px;font-weight:700"); self.scan_button.clicked.connect(self.run_market_scan)
        self.result_box=QTextEdit(); self.result_box.setReadOnly(True); self.result_box.setStyleSheet("font-size:16px")
        if not self.scanner_enabled:
            self.scan_button.setEnabled(False); self.result_box.setText("РЕЖИМ ПРОСМОТРА\n\nБКС временно недоступен.\nСканирование будет доступно после восстановления подключения.")
        else:self.result_box.setText("БКС ПОДКЛЮЧЁН\n\nНажмите «СКАНИРОВАТЬ РЫНОК».\nРадар выберет TOP 2–3 фьючерса по текущей рыночной ситуации.")
        layout=QVBoxLayout(); layout.setContentsMargins(18,14,18,18); layout.setSpacing(7)
        for w in (self.title,self.subtitle,self.session_label,self.clock_label,self.scan_button,self.result_box):layout.addWidget(w)
        self.setLayout(layout)

    def _set_scan_button_style(self,color="#c9d0d6"):
        self.scan_button.setStyleSheet(f"font-size:18px;font-weight:700;color:{color};background:#30373f;border:1px solid #46505a;border-radius:8px;padding:10px 18px")

    def _update_session_header(self):
        info=self.session_service.get_session_info(); session=info.get("session","CLOSED")
        self.session_label.setText(SESSION_LABELS.get(session,session))
        self.clock_label.setText(f"{info.get('date','—')}  •  МСК {info.get('time','—')}  •  {'РЫНОК ОТКРЫТ' if info.get('market_open') else 'РЫНОК ЗАКРЫТ'}")
        self.subtitle.setText({"PRE_OPEN":"ПОДГОТОВКА • 06:50–07:00 МСК","MORNING":"УТРЕННИЙ РАДАР • 07:00–10:00 МСК","MAIN":"ОСНОВНАЯ СЕССИЯ • 10:00–19:00 МСК","EVENING":"ВЕЧЕРНИЙ РАДАР • 19:00–23:50 МСК","CLOSED":"РЫНОК ЗАКРЫТ • 23:50–06:50 МСК"}.get(session,"РЫНОЧНЫЙ РАДАР"))

    def _animate_scan(self):
        self.animation_step=(self.animation_step+1)%4
        self.scan_button.setText("●  ИДЁТ СКАНИРОВАНИЕ")
        self._set_scan_button_style(["#9fba5d","#b7d96b","#d0e58a","#b7d96b"][self.animation_step])

    def _start_scan_animation(self):
        self.animation_step=0; self.scan_animation_timer.start(260); self._animate_scan()

    def _stop_scan_animation(self,text="●  ГОТОВО"):
        self.scan_animation_timer.stop(); self.scan_button.setText(text); self._set_scan_button_style()

    def run_market_scan(self):
        if not self.scanner_enabled:return self.result_box.setText("РЕЖИМ ПРОСМОТРА\n\nБКС временно недоступен. Сканирование невозможно.")
        if self.scan_thread is not None and self.scan_thread.isRunning():return
        self.result_box.setText("АНАЛИЗ РЫНКА\n\nBCS → SPOT → ЛИКВИДНОСТЬ → ТЕКУЩАЯ СЕССИЯ → RS → SETUP → FUTURES\n\nАнализ выполняется в фоне.")
        self.scan_button.setEnabled(False); self._start_scan_animation()
        try:
            if self.scanner is None:
                from services.morning_trading_pipeline_service import MorningTradingPipelineService
                self.scanner=MorningTradingPipelineService()
            self.scan_thread=QThread(self); self.scan_worker=MarketScanWorker(self.scanner,limit=3); self.scan_worker.moveToThread(self.scan_thread)
            self.scan_thread.started.connect(self.scan_worker.run); self.scan_worker.finished.connect(self._scan_finished); self.scan_worker.failed.connect(self._scan_failed)
            self.scan_worker.finished.connect(self.scan_thread.quit); self.scan_worker.failed.connect(self.scan_thread.quit); self.scan_thread.finished.connect(self._scan_thread_finished); self.scan_thread.start()
        except Exception as exc:self._scan_failed(f"{type(exc).__name__}: {exc}")

    def _scan_finished(self,results):
        self.scan_button.setEnabled(True); self._stop_scan_animation()
        info=self.session_service.get_session_info(); session=info.get("session","CLOSED"); session_name=SESSION_LABELS.get(session,session)
        html=["<pre style='font-family:Menlo,Monaco,monospace;font-size:14px;color:#dfe3e7'>","═"*78,"TRADER_7_12 PRO — TOP 2–3 ФЬЮЧЕРСА","═"*78,"",f"{escape(session_name)} • {escape(info.get('date','—'))} • МСК {escape(info.get('time','—'))}","","ГДЕ ДЕНЬГИ • ГДЕ СИЛА/СЛАБОСТЬ • ГДЕ ЕСТЬ ПОТЕНЦИАЛ ДВИЖЕНИЯ",""]
        if not results:
            html += ["","ГОТОВЫХ КАНДИДАТОВ НЕТ","","Ни один инструмент не прошёл обязательные проверки в текущей сессии.","</pre>"]; self.result_box.setHtml("\n".join(html)); return
        for index,item in enumerate(results,1):
            direction=str(item.get("direction") or "-").upper(); color=LONG_COLOR if direction=="LONG" else SHORT_COLOR if direction=="SHORT" else "#dfe3e7"
            trigger=item.get("entry_trigger")
            if not trigger or float(trigger or 0)==0:trigger=item.get("previous_high") if direction=="LONG" else item.get("previous_low")
            ratio=float(item.get("spot_money_ratio",0) or 0); change=item.get("price_change_percent",0)
            ticker=f"{escape(str(item.get('futures_ticker','-')))}  /  {escape(str(item.get('spot_ticker','-')))}"
            direction_text=escape(_label(DIRECTION_LABELS,direction))
            html += ["",f"<span style='color:{color};font-weight:700'>████  #{index}  {ticker}  ████</span>",f"<span style='color:{color};font-weight:700'>НАПРАВЛЕНИЕ:       {direction_text}</span>",f"СЕССИОННАЯ ОЦЕНКА: {_number(item.get('session_rank_score'),1)} / 100",f"ОЦЕНКА:            {_number(item.get('candidate_score'),1)} / 100",f"RS:                {escape(_rs_label(item))}",f"АКТИВНОСТЬ SPOT:   {escape(_activity_label(item))} ({_number(ratio,2)}× среднего)",f"СЕТАП:             {escape(_label(SETUP_LABELS,item.get('setup')))}",f"СОСТОЯНИЕ:          {escape(_label(SETUP_STATE_LABELS,item.get('setup_state')))}","",f"SPOT ЦЕНА:          {_number(item.get('spot_price'),4)}",f"ФЬЮЧЕРС ЦЕНА:       {_number(item.get('futures_price'),4)}",f"SPOT СРЕДНИЙ ₽×V:   {_money(item.get('spot_average_daily_money',item.get('average_daily_money')))}",f"SPOT СЕССИЯ ₽×V:    {_money(item.get('spot_money_volume'))}",f"SPOT ₽×V/МИН:       {_money(item.get('spot_money_per_minute'))}",f"ФЬЮЧЕРС ₽×V:        {_money(item.get('money_volume'))}",f"СДЕЛОК:             {int(item.get('trade_count',0) or 0):,}".replace(","," "),f"ДВИЖЕНИЕ ФЬЮЧЕРСА:  {_number(change,2)}%","",f"ЛОКАЛЬНЫЙ МАКСИМУМ: {_number(item.get('previous_high'),4)}",f"ЛОКАЛЬНЫЙ МИНИМУМ:  {_number(item.get('previous_low'),4)}",f"ТРИГГЕР УРОВНЯ:     {_number(trigger,4)}","","─"*78]
        strategy=results[0].get("session_strategy") or results[0].get("strategy")
        if strategy:html += ["",f"СТРАТЕГИЯ СЕССИИ: {escape(str(strategy))}"]
        html += ["","ВАЖНО: это АНАЛИТИЧЕСКИЙ РАДАР.","Пользователь самостоятельно смотрит график и принимает решение о входе.","Никакого position sizing, SL/TP или исполнения ордеров нет.","</pre>"]
        self.result_box.setHtml("\n".join(html))

    def _scan_failed(self,error):
        self.scan_button.setEnabled(True); self._stop_scan_animation("●  ОШИБКА СКАНИРОВАНИЯ")
        self.result_box.setText(f"ОШИБКА СКАНИРОВАНИЯ\n\n{error}\n\nБКС мог временно не ответить. Повторите сканирование.")
    def _scan_thread_finished(self):
        if self.scan_worker is not None:self.scan_worker.deleteLater()
        if self.scan_thread is not None:self.scan_thread.deleteLater()
        self.scan_worker=None; self.scan_thread=None
    def closeEvent(self,event):
        self.scan_animation_timer.stop(); self.clock_timer.stop()
        if self.scan_thread is not None and self.scan_thread.isRunning():self.scan_thread.quit(); self.scan_thread.wait(3000)
        event.accept()
