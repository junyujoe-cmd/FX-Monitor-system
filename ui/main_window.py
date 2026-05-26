from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QTabWidget, QLabel, QStatusBar, QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, Qt
from datetime import datetime
from config import FETCH_INTERVAL_SECONDS, BANK_SPREADS
from database import Database
from fetcher import fetch_all_quotes
from bank_fetcher import fetch_boc_rates, fetch_cmb_rates, fetch_boc_history
from ui.quote_bar import QuoteBar
from ui.compare_panel import ComparePanel
from ui.chart_widget import ChartWidget


class FetchWorker(QThread):
    finished = pyqtSignal(str, dict, dict, dict)

    def run(self):
        cycle_id = datetime.now().isoformat()
        quotes = fetch_all_quotes() or {}
        boc = fetch_boc_rates() or {}
        cmb = fetch_cmb_rates() or {}
        self.finished.emit(cycle_id, quotes, boc, cmb)


class CalculatorBridge:
    def __init__(self, db):
        self.db = db
        self.cached_quotes = {}

    def set_market_quotes(self, quotes):
        self.cached_quotes = quotes

    def get_latest_market_quotes(self):
        return self.cached_quotes

    def compute_entry(self, pair, user_quote, direction):
        market = self.cached_quotes.get(pair, {})
        market_bid = market.get("bid")
        market_ask = market.get("ask")
        market_mid = market.get("mid")

        bank_bid = market_bid if market_bid is not None else market_mid
        bank_ask = market_ask if market_ask is not None else market_mid

        result = compute_entry_result(user_quote, direction,
                                       market_bid if market_bid is not None else market_mid,
                                       market_ask if market_ask is not None else market_mid,
                                       bank_bid, bank_ask)
        self.db.save_user_entry(
            pair=pair, bank="手动录入", direction=direction,
            user_quote=user_quote,
            market_cost=result["market_cost"],
            bank_cost=result["bank_cost"],
            bp_vs_market=result["bp_vs_market"],
            bp_vs_bank=result["bp_vs_bank"],
        )
        return result


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("实时外汇监控系统")
        self.resize(1200, 800)

        self.db = Database()
        self.calculator = CalculatorBridge(self.db)
        self._tray_shown = False

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        self.quote_bar = QuoteBar()
        layout.addWidget(self.quote_bar, stretch=1)

        self.tabs = QTabWidget()
        self.compare_panel = ComparePanel(self.db, self.calculator)
        self.chart_widget = ChartWidget(self.db)

        self.tabs.addTab(self.compare_panel, "录入报价")
        self.tabs.addTab(self.chart_widget, "历史图表")

        layout.addWidget(self.tabs, stretch=1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("就绪")
        self.status_bar.addWidget(self.status_label)

        self.tray_icon = QSystemTrayIcon(self)
        icon = self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon)
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("实时外汇监控系统")
        tray_menu = QMenu()
        show_action = QAction("显示窗口", self)
        show_action.triggered.connect(self.showNormal)
        tray_menu.addAction(show_action)
        quit_action = QAction("退出程序", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)

        if not self.db.has_boc_history():
            QTimer.singleShot(1000, self._backfill_history)

        self.timer = QTimer()
        self.timer.timeout.connect(self._fetch_data)
        self.timer.start(FETCH_INTERVAL_SECONDS * 1000)
        self._fetch_busy = False

        self._fetch_data()

    def _fetch_data(self):
        if self._fetch_busy:
            return
        self._fetch_busy = True
        self.status_label.setText("正在获取数据...")
        self.worker = FetchWorker()
        self.worker.finished.connect(self._on_data_fetched)
        self.worker.start()

    def _on_data_fetched(self, cycle_id, quotes, boc_rates, cmb_rates):
        if not quotes:
            self.status_label.setText(f"数据获取失败 ({datetime.now().strftime('%H:%M:%S')})")
            return

        self.db.save_market_quotes_batch(cycle_id, quotes, "CFETS")

        bank_data = []
        for pair, data in quotes.items():
            mid = data["mid"]
            for bank, spread in BANK_SPREADS.items():
                if bank == "中国银行" and boc_rates and pair in boc_rates:
                    r = boc_rates[pair]
                    bid, ask = r["bid"], r["ask"]
                elif bank == "招商银行" and cmb_rates and pair in cmb_rates:
                    r = cmb_rates[pair]
                    bid, ask = r["bid"], r["ask"]
                else:
                    bid = round(mid + spread["bid_offset"], 4)
                    ask = round(mid + spread["ask_offset"], 4)
                bank_data.append((bank, pair, bid, ask))
        self.db.save_bank_quotes_batch(cycle_id, bank_data)

        bank_quotes_full = {}
        if boc_rates:
            bank_quotes_full["中国银行"] = boc_rates
        if cmb_rates:
            bank_quotes_full["招商银行"] = cmb_rates

        self.calculator.set_market_quotes(quotes)
        self.quote_bar.update_all(quotes, bank_quotes_full)
        self.compare_panel.update_bank_data(quotes, bank_quotes_full)
        self.chart_widget.refresh()
        self.status_label.setText(f"最后更新: {datetime.now().strftime('%H:%M:%S')}")
        self._fetch_busy = False

    def _backfill_history(self):
        self.status_label.setText("正在导入中行历史数据...")
        hist = fetch_boc_history(days=30)
        if hist:
            self.db.save_boc_history(hist)
            self.status_label.setText(f"已导入 {len(hist)} 条中行历史数据")
            self.chart_widget.refresh()
        else:
            self.status_label.setText("中行历史数据导入失败")

    def closeEvent(self, event):
        self.hide()
        if not self._tray_shown:
            self._tray_shown = True
            self.tray_icon.show()
        event.ignore()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.DoubleClick, QSystemTrayIcon.ActivationReason.Trigger):
            self.showNormal()
            self.raise_()
