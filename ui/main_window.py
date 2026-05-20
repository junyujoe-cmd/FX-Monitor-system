from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QTabWidget, QLabel, QStatusBar
from PyQt6.QtCore import QTimer, QThread, pyqtSignal
from datetime import datetime
from config import FETCH_INTERVAL_SECONDS
from database import Database
from calculator import compute_entry_result
from fetcher import fetch_all_quotes
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

        result = compute_entry_result(user_quote, direction, market_bid, market_ask, bank_bid, bank_ask)
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
        self.resize(1000, 700)

        self.db = Database()
        self.calculator = CalculatorBridge(self.db)

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

        self.tabs.addTab(self.compare_panel, "银行对比 + 录入")
        self.tabs.addTab(self.chart_widget, "历史图表")

        layout.addWidget(self.tabs)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("就绪")
        self.status_bar.addWidget(self.status_label)

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
        self.db.save_market_quotes_batch(cycle_id, quotes, "open-er-api")
        self.calculator.set_market_quotes(quotes)
        self.quote_bar.update_all(quotes)
        self.compare_panel.update_bank_data(quotes)
        self.chart_widget.refresh()
        self.status_label.setText(f"最后更新: {datetime.now().strftime('%H:%M:%S')}")
