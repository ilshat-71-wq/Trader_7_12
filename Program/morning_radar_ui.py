"""Morning Radar presentation for Trader_7_12 Pro.

Read-only client for the Cloud Market Data Engine. It never calculates or
requests a second market scan; it displays the persisted morning snapshots.
"""
from __future__ import annotations

import json
import os
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

from PySide6.QtCore import QObject, QThread, Signal, Qt, QTimer
from PySide6.QtGui import QColor, QFont
from services.signal_probability_service import SignalProbabilityService

from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)


class MorningRadarWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url.rstrip("/") + "/v1/morning-radar"

    def run(self):
        try:
            request = Request(self.url, headers={"Accept": "application/json"})
            with urlopen(request, timeout=6) as response:
                payload = json.loads(response.read().decode("utf-8"))
            self.finished.emit(payload)
        except (URLError, HTTPError, TimeoutError, ValueError) as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class MorningRadarWidget(QWidget):
    """Premium compact morning history: interest + countertrend weakness."""

    CLOUD_URL_ENV = "TRADER_CLOUD_URL"
    DEFAULT_CLOUD_URL = "http://127.0.0.1:8080"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._worker = None
        self._payload = None
        self.signal_probability = SignalProbabilityService()
        self._build()

    def _build(self):
        self.setStyleSheet("""
            QLabel#mrTitle { font-size:17px; font-weight:800; color:#e8ecef; }
            QLabel#mrMeta { font-size:11px; color:#8d98a2; }
            QLabel#mrState { font-size:12px; font-weight:800; color:#d4af55; }
            QPushButton { background:#30383f; color:#f0f2f4; border:1px solid #4a555f;
                          border-radius:7px; padding:8px 13px; font-weight:700; }
            QPushButton:hover { background:#39434c; }
            QTableWidget { background:#171b20; color:#dfe3e7; border:1px solid #394149;
                           gridline-color:#2d343b; font-size:11px; }
            QHeaderView::section { background:#252c33; color:#b9c2ca; padding:7px;
                                   border:0; border-bottom:1px solid #414a52; font-weight:700; }
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        head = QHBoxLayout()
        title = QLabel("MORNING RADAR")
        title.setObjectName("mrTitle")
        head.addWidget(title)
        self.state = QLabel("NO DATA")
        self.state.setObjectName("mrState")
        head.addWidget(self.state)
        head.addStretch(1)
        self.refresh_button = QPushButton("REFRESH")
        self.refresh_button.clicked.connect(self.refresh)
        head.addWidget(self.refresh_button)
        self.copy_button = QPushButton("COPY")
        self.copy_button.setToolTip("Copy the visible Morning Radar table and summary")
        self.copy_button.clicked.connect(self.copy_view)
        head.addWidget(self.copy_button)
        root.addLayout(head)

        self.meta = QLabel(
            "WHO TO WATCH • 06:50 → 09:00 MSK • futures-first morning shortlist • "
            "at 09:00 the app hands off to ENTRY RADAR"
        )
        self.meta.setObjectName("mrMeta")
        root.addWidget(self.meta)

        self.summary = QLabel("Morning Radar loads from the Cloud Market Data Engine.")
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet(
            "background:#171b20;border:1px solid #394149;border-radius:8px;"
            "padding:9px 12px;font-size:11px;color:#c9d0d6;"
        )
        root.addWidget(self.summary)

        watch_title = QLabel("TODAY'S WATCHLIST")
        watch_title.setStyleSheet("font-size:12px;font-weight:800;color:#e8ecef;padding-top:2px;")
        root.addWidget(watch_title)
        self.watchlist_table = QTableWidget(0, 7)
        self.watchlist_table.setHorizontalHeaderLabels([
            "#", "Instrument", "Direction", "Strength", "Interest", "Setup", "Entry"
        ])
        self.watchlist_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.watchlist_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.watchlist_table.setAlternatingRowColors(True)
        self.watchlist_table.verticalHeader().setVisible(False)
        self.watchlist_table.horizontalHeader().setStretchLastSection(True)
        self.watchlist_table.setToolTip(
            "WHO TO WATCH before the main futures session. Strength = existing futures model confidence. "
            "Interest = change in that confidence between morning snapshots. Setup describes the current structure; "
            "Entry stays in ENTRY RADAR after the 09:00 handoff."
        )
        root.addWidget(self.watchlist_table)

        details_title = QLabel("MORNING DETAILS")
        details_title.setStyleSheet("font-size:11px;font-weight:800;color:#8d98a2;padding-top:3px;")
        root.addWidget(details_title)
        self.table = QTableWidget(0, 11)
        self.table.setHorizontalHeaderLabels([
            "Ticker", "Price Δ%", "RS", "₽/min", "15m Δ%",
            "Accel", "Interest", "SHORT WATCH", "PERSIST", "SIGNAL", "PROB",
        ])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(False)
        root.addWidget(self.table, 1)

        self.oi_summary = QLabel("OI HISTORY: —")
        self.oi_summary.setStyleSheet("font-size:10px;color:#7f8a94;padding:3px;")
        root.addWidget(self.oi_summary)

    @classmethod
    def cloud_url(cls):
        return os.getenv(cls.CLOUD_URL_ENV, cls.DEFAULT_CLOUD_URL).strip()

    def refresh(self):
        if self._thread is not None and self._thread.isRunning():
            return
        self.refresh_button.setEnabled(False)
        self.state.setText("LOADING…")
        self._thread = QThread(self)
        self._worker = MorningRadarWorker(self.cloud_url())
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._finished)
        self._worker.failed.connect(self._failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._thread_finished)
        self._thread.start()

    def _finished(self, payload):
        self._payload = payload or {}
        captured = self._payload.get("completed_slots") or []
        complete = "09:50" in captured
        self.state.setText("COMPLETE • 09:50" if complete else f"{len(captured)}/7 SLOTS")
        self.state.setStyleSheet(
            "font-size:12px;font-weight:800;color:" +
            ("#69e59a" if complete else "#d4af55") + ";"
        )
        self.meta.setText(
            f"{self._payload.get('trading_date', self._payload.get('date','—'))} MSK • "
            f"SLOTS {', '.join(captured) if captured else '—'} • "
            f"CLOUD {self.cloud_url()}"
        )
        history = self._payload.get("history") or []
        latest = self._payload.get("latest") or {}
        radar_rows = list(latest.get("radar") or [])
        countertrend = list(latest.get("countertrend_watch") or [])
        stocks = [dict(x, short_watch=False) for x in radar_rows]
        stocks.extend(dict(x, short_watch=True) for x in countertrend)
        regime = str(latest.get("market_regime") or "—")
        benchmark = latest.get("benchmark_change_percent")
        short_count = len(countertrend)
        persistent_short = sum(1 for x in countertrend if int(x.get("short_watch_persistence") or 0) >= 2)
        rising_interest = sum(1 for x in radar_rows if (x.get("interest") or {}).get("state") == "RISING")
        self.summary.setText(
            f"REGIME {regime} • IMOEX2 {benchmark if benchmark is not None else '—'}% • "
            f"INTEREST ↑ {rising_interest} • SHORT WATCH {short_count} • "
            f"PERSISTENT SHORT {persistent_short} • "
            f"SNAPSHOTS {len(history)}.  "
            "Interest uses changes in existing 15m/rate/acceleration fields; "
            "SHORT WATCH is a separate weakness lane, not a trade order."
        )

        # Futures-first compact watchlist: it answers WHO is interesting
        # before the main session. The detailed SPOT history remains below.
        latest_futures = list(latest.get("futures_oi") or [])
        previous_futures = list((history[-2] if len(history) > 1 else {}).get("futures_oi") or [])
        previous_by_contract = {
            str(x.get("futures_ticker") or x.get("oi_root") or "").upper(): x
            for x in previous_futures
        }
        future_rows = []
        for item in latest_futures:
            model = self.signal_probability.futures(item)
            key = str(item.get("futures_ticker") or item.get("oi_root") or "").upper()
            previous = previous_by_contract.get(key)
            previous_prob = self.signal_probability.futures(previous)["probability"] if previous else None
            enriched = dict(item)
            enriched.update({
                "signal": model["signal"],
                "signal_probability": model["probability"],
                "signal_probability_delta": round(model["probability"] - previous_prob, 1) if previous_prob is not None else None,
            })
            future_rows.append(enriched)
        future_rows.sort(key=lambda x: float(x.get("signal_probability") or 0.0), reverse=True)
        watch_rows = future_rows[:5]
        self.watchlist_table.setRowCount(len(watch_rows))
        for r, item in enumerate(watch_rows, 1):
            signal = str(item.get("signal") or "").upper()
            direction = {"LONG": "🟢 LONG", "SHORT": "🔴 SHORT", "NEUTRAL": "⚪ NEUTRAL"}.get(signal, "⚪ —")
            strength = f"{float(item.get('signal_probability')):.0f}" if item.get("signal_probability") is not None else "—"
            delta = item.get("signal_probability_delta")
            if delta is None:
                interest = "NEW"
            elif float(delta) > 1.0:
                interest = "↑"
            elif float(delta) < -1.0:
                interest = "↓"
            else:
                interest = "→"
            action = str(item.get("money_flow_position_action") or "").upper()
            setup = "DEVELOPING" if interest == "↑" else ("WATCH" if interest in {"→", "NEW"} else "WEAKENING")
            if action == "LONG_LIQUIDATION":
                setup = "LIQUIDATION"
            elif action == "SHORT_COVERING":
                setup = "COVERING"
            values = [str(r), str(item.get("futures_ticker") or item.get("oi_root") or "—"), direction, strength, interest, setup, "—"]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter if col in (0, 2, 3, 4, 5, 6) else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self.watchlist_table.setItem(r - 1, col, cell)
            bg = QColor("#123f2a") if interest == "↑" else QColor("#252b31")
            if setup == "LIQUIDATION":
                bg = QColor("#3a272b")
            for col in range(self.watchlist_table.columnCount()):
                self.watchlist_table.item(r - 1, col).setBackground(bg)
            self.watchlist_table.item(r - 1, 2).setForeground(QColor("#69e59a" if signal == "LONG" else "#ff7d7d" if signal == "SHORT" else "#c9d0d6"))
            self.watchlist_table.item(r - 1, 3).setForeground(QColor("#e8ecef"))
            self.watchlist_table.item(r - 1, 4).setForeground(QColor("#69e59a" if interest == "↑" else "#ff7d7d" if interest == "↓" else "#d4af55"))

        rows = sorted(
            stocks,
            key=lambda x: (
                0 if x.get("short_watch") else 1,
                0 if (x.get("interest") or {}).get("state") == "RISING" else 1,
                -(float(x.get("relative_strength") or 0.0)),
            ),
        )
        self.table.setRowCount(len(rows))
        for r, item in enumerate(rows):
            values = [
                item.get("spot_ticker") or item.get("ticker") or "—",
                self._fmt(item.get("change_percent")),
                self._fmt(item.get("relative_strength")),
                self._fmt(item.get("money_per_minute"), 0),
                self._fmt((item.get("interest") or {}).get("recent_pace_delta_pct")),
                self._fmt(item.get("money_acceleration")),
                str((item.get("interest") or {}).get("state") or "—"),
                "● SHORT WATCH" if item.get("short_watch") else "—",
                f"{int(item.get('short_watch_persistence') or 0)}/{len(captured)}" if item.get("short_watch") else "—",
                str(item.get("signal") or "—"),
                self._fmt(item.get("signal_probability")),
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if col in (1, 2, 3, 4, 5, 10):
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(r, col, cell)
            if item.get("short_watch"):
                for col in range(self.table.columnCount()):
                    self.table.item(r, col).setBackground(QColor("#3a272b"))
            elif (item.get("interest") or {}).get("state") == "RISING":
                for col in range(self.table.columnCount()):
                    self.table.item(r, col).setBackground(QColor("#123f2a"))
            if (item.get("interest") or {}).get("state") == "RISING":
                self.table.item(r, 6).setForeground(QColor("#69e59a"))
            if item.get("short_watch"):
                self.table.item(r, 7).setForeground(QColor("#ff7d7d"))
                self.table.item(r, 8).setForeground(QColor("#ff7d7d"))

        oi = latest.get("futures_oi") or []
        oi_hot = sum(
            1 for x in oi if str(x.get("money_flow_liquidity_state") or "") == "HOT"
        )
        oi_flow = sum(
            1 for x in oi if str(x.get("money_flow_status") or "") == "AVAILABLE"
        )
        self.oi_summary.setText(
            f"OI HISTORY: {len(oi)} contracts • FLOW {oi_flow} available • "
            f"HOT LIQ {oi_hot} • latest slot {latest.get('slot','—')}"
        )

    def copy_view(self):
        lines = [self.summary.text(), self.meta.text()]
        headers = [
            self.table.horizontalHeaderItem(i).text()
            for i in range(self.table.columnCount())
        ]
        lines.append("\t".join(headers))
        for row in range(self.table.rowCount()):
            lines.append(
                "\t".join(
                    self.table.item(row, col).text() if self.table.item(row, col) else ""
                    for col in range(self.table.columnCount())
                )
            )
        lines.append(self.oi_summary.text())
        QApplication.clipboard().setText("\n".join(lines))
        self.copy_button.setText("COPIED ✓")
        QTimer.singleShot(1400, lambda: self.copy_button.setText("COPY"))

    def _failed(self, error):
        self.state.setText("OFFLINE")
        self.state.setStyleSheet("font-size:12px;font-weight:800;color:#ff7d7d;")
        self.summary.setText(
            f"Morning Radar cloud is unavailable: {error}. "
            "The desktop scanner remains unchanged."
        )

    def _thread_finished(self):
        if self._thread is not None:
            self._thread.deleteLater()
        self._thread = None
        self._worker = None
        self.refresh_button.setEnabled(True)

    @staticmethod
    def _fmt(value, digits=1):
        try:
            return f"{float(value):+,.{digits}f}".replace(",", " ")
        except (TypeError, ValueError):
            return "—"
