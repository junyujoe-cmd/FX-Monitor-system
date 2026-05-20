from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QTabWidget, QLabel, QStatusBar, QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, Qt
from datetime import datetime
from config import FETCH_INTERVAL_SECONDS, BANK_SPREADS
from database import Database
from fetcher import fetch_all_quotes
from bank_fetcher import fetch_boc_rates, fetch_cmb_rates
from ui.quote_bar import QuoteBar
from ui.compare_panel import ComparePanel
from ui.chart_widget import ChartWidget


class FetchWorker(QThread):
    finished = pyqtSignal(str, dict)

    def run(self):
        cycle_id = datetime.now().isoformat()
        quotes = fetch_all_quotes()
        if quotes:
            self.finished.emit(cycle_id, quotes)


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
        self.resize(1100, 750)

        self.db = Database()
        self.calculator = CalculatorBridge(self.db)
        self._tray_shown = False

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        self.quote_bar = QuoteBar()
        layout.addWidget(self.quote_bar)

        self.tabs = QTabWidget()
        self.compare_panel = ComparePanel(self.db, self.calculator)
        self.chart_widget = ChartWidget(self.db)

        self.tabs.addTab(self.compare_panel, "录入报价")
        self.tabs.addTab(self.chart_widget, "历史图表")

        layout.addWidget(self.tabs)

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

        self.timer = QTimer()
        self.timer.timeout.connect(self._fetch_data)
        self.timer.start(FETCH_INTERVAL_SECONDS * 1000)

        self._fetch_data()

    def _fetch_data(self):
        self.status_label.setText("正在获取数据...")
        self.worker = FetchWorker()
        self.worker.finished.connect(self._on_data_fetched)
        self.worker.start()

    def _on_data_fetched(self, cycle_id, quotes):
        self.db.save_market_quotes_batch(cycle_id, quotes, "CFETS")

        boc_rates = fetch_boc_rates()
        cmb_rates = fetch_cmb_rates()

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

        self.calculator.set_market_quotes(quotes)
        self.quote_bar.update_all(quotes)
        self.compare_panel.update_bank_data(quotes)
        self.chart_widget.refresh()
        self.status_label.setText(f"最后更新: {datetime.now().strftime('%H:%M:%S')}")

    def closeEvent(self, event):
        self.tray_icon.show()
        self.hide()
        if not self._tray_shown:
            self._tray_shown = True
            self.tray_icon.showMessage(
                "后台运行中",
                "外汇监控系统已最小化到系统托盘，将继续在后台采集数据。\n"
                "点击托盘图标可重新显示窗口。\n右键托盘图标选择「退出程序」彻底关闭。",
                QSystemTrayIcon.MessageIcon.Information,
                5000,
            )
        event.ignore()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.showNormal()
            self.raise_()
