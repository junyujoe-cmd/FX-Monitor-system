# 实时外汇监控系统 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个可运行的 PyQt6 桌面外汇监控系统，包含实时报价、银行对比、用户录入和历史图表。

**Architecture:** 单进程 PyQt6 应用，QTimer+QThread 后台抓取数据，SQLite 本地存储。UI 模块化拆分（报价条、对比面板、图表）。

**Tech Stack:** Python 3, PyQt6, SQLite3, requests, pyqtgraph

---

### Task 1: 项目脚手架 — config + requirements + main.py 骨架

**Files:**
- Create: `forex-monitor/config.py`
- Create: `forex-monitor/requirements.txt`
- Create: `forex-monitor/main.py`

- [ ] **Step 1: 创建 config.py**

```python
CURRENCY_PAIRS = ["USDCNY", "EURCNY", "HKDCNY", "JPYCNY"]

BANKS = ["中国银行", "招商银行", "宁波银行", "杭州银行"]

# 免费汇率 API（备用多个来源）
API_URLS = {
    "exchangerate-api": "https://api.exchangerate-api.com/v4/latest/USD",
    "openexchangerates": "https://open.er-api.com/v6/latest/USD",
}

FETCH_INTERVAL_SECONDS = 60
DB_PATH = "forex_data.db"
```

- [ ] **Step 2: 创建 requirements.txt**

```
PyQt6>=6.5
requests>=2.31
pyqtgraph>=0.13
```

- [ ] **Step 3: 创建 main.py 骨架**

```python
import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("实时外汇监控系统")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 创建 ui/ 包**

```bash
mkdir -p forex-monitor/ui
touch forex-monitor/ui/__init__.py
```

- [ ] **Step 5: 验证 import**

Run: `python -c "from config import CURRENCY_PAIRS, BANKS; print('config OK')"`
Expected: `config OK`

- [ ] **Step 6: Commit**

```bash
git add config.py requirements.txt main.py ui/__init__.py
git commit -m "feat: project scaffold with config and entry point"
```

---

### Task 2: 数据库模块 — database.py

**Files:**
- Create: `forex-monitor/database.py`

- [ ] **Step 1: 创建 database.py**

```python
import sqlite3
from datetime import datetime
from config import DB_PATH


class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_tables()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_tables(self):
        conn = self._get_conn()
        c = conn.cursor()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS market_quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                pair TEXT NOT NULL,
                bid REAL,
                ask REAL,
                mid REAL,
                source TEXT
            );
            CREATE TABLE IF NOT EXISTS bank_quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                bank TEXT NOT NULL,
                pair TEXT NOT NULL,
                bid REAL,
                ask REAL
            );
            CREATE TABLE IF NOT EXISTS user_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                pair TEXT NOT NULL,
                bank TEXT NOT NULL,
                direction TEXT NOT NULL,
                user_quote REAL,
                market_cost REAL,
                bank_cost REAL,
                bp_vs_market REAL,
                bp_vs_bank REAL
            );
        """)
        conn.commit()
        conn.close()

    def save_market_quote(self, pair, bid, ask, mid, source):
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO market_quotes (timestamp, pair, bid, ask, mid, source) VALUES (?, ?, ?, ?, ?, ?)",
            (datetime.now().isoformat(), pair, bid, ask, mid, source),
        )
        conn.commit()
        conn.close()

    def get_latest_market_quote(self, pair):
        conn = self._get_conn()
        row = conn.execute(
            "SELECT bid, ask, mid FROM market_quotes WHERE pair = ? ORDER BY id DESC LIMIT 1",
            (pair,),
        ).fetchone()
        conn.close()
        return row  # (bid, ask, mid) or None

    def get_recent_market_quotes(self, pair, limit=100):
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT timestamp, bid, ask, mid FROM market_quotes WHERE pair = ? ORDER BY id DESC LIMIT ?",
            (pair, limit),
        ).fetchall()
        conn.close()
        return list(reversed(rows))

    def save_user_entry(self, pair, bank, direction, user_quote, market_cost, bank_cost, bp_vs_market, bp_vs_bank):
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO user_entries (timestamp, pair, bank, direction, user_quote, market_cost, bank_cost, bp_vs_market, bp_vs_bank) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (datetime.now().isoformat(), pair, bank, direction, user_quote, market_cost, bank_cost, bp_vs_market, bp_vs_bank),
        )
        conn.commit()
        conn.close()

    def get_recent_user_entries(self, limit=20):
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT timestamp, pair, bank, direction, user_quote, market_cost, bank_cost, bp_vs_market, bp_vs_bank FROM user_entries ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return list(reversed(rows))
```

- [ ] **Step 2: 验证数据库初始化**

Run: `python -c "from database import Database; db = Database(':memory:'); print('database OK')"`
Expected: `database OK`

- [ ] **Step 3: Commit**

```bash
git add database.py
git commit -m "feat: SQLite database module with tables for market quotes, bank quotes, user entries"
```

---

### Task 3: 计算模块 — calculator.py

**Files:**
- Create: `forex-monitor/calculator.py`

- [ ] **Step 1: 创建 calculator.py**

```python
def calculate_bp(quote, cost):
    """计算基点差。1bp = 0.0001 外汇单位"""
    if cost == 0:
        return 0.0
    return round((quote - cost) / cost * 10000, 1)


def market_cost_price(market_bid, market_ask):
    """市场成本 = CFETS 中间价"""
    if market_bid and market_ask:
        return round((market_bid + market_ask) / 2, 4)
    return market_bid or market_ask


def bank_cost_price(bank_bid, bank_ask):
    """银行自身成本 = (该银行买价+卖价)/2"""
    return round((bank_bid + bank_ask) / 2, 4)


def compute_entry_result(user_quote, direction, market_bid, market_ask, bank_bid, bank_ask):
    """
    计算用户录入报价后的结果。
    direction: '买入价' or '卖出价'
    返回 dict 包含所有成本价和 bp 差。
    """
    market_mid = market_cost_price(market_bid, market_ask)
    bank_mid = bank_cost_price(bank_bid, bank_ask)

    bp_vs_market = calculate_bp(user_quote, market_mid)
    bp_vs_bank = calculate_bp(user_quote, bank_mid)

    return {
        "market_cost": market_mid,
        "bank_cost": bank_mid,
        "bp_vs_market": bp_vs_market,
        "bp_vs_bank": bp_vs_bank,
    }
```

- [ ] **Step 2: 验证计算逻辑**

Run:
```bash
python -c "
from calculator import calculate_bp, market_cost_price, bank_cost_price, compute_entry_result

# 测试 calculate_bp
assert calculate_bp(7.2480, 7.2400) == 11.0, f'got {calculate_bp(7.2480, 7.2400)}'
print('bp test pass')

# 测试成本价
assert market_cost_price(7.2400, 7.2440) == 7.2420
assert bank_cost_price(7.2380, 7.2480) == 7.2430
print('cost price test pass')

# 测试完整计算
res = compute_entry_result(7.2480, '买入价', 7.2400, 7.2440, 7.2380, 7.2480)
assert res['market_cost'] == 7.2420
assert res['bank_cost'] == 7.2430
print(f'Result: {res}')
print('ALL OK')
"
```
Expected: `ALL OK`

- [ ] **Step 3: Commit**

```bash
git add calculator.py
git commit -m "feat: calculator module for bp and cost price computation"
```

---

### Task 4: 数据抓取模块 — fetcher.py

**Files:**
- Create: `forex-monitor/fetcher.py`

- [ ] **Step 1: 创建 fetcher.py**

```python
import requests
from datetime import datetime
from config import CURRENCY_PAIRS


def fetch_exchangerate_api():
    """从免费 API 获取 USD 基准汇率，推算各货币对"""
    try:
        resp = requests.get("https://open.er-api.com/v6/latest/CNY", timeout=10)
        data = resp.json()
        rates = data.get("rates", {})

        return {
            "USDCNY": {"bid": None, "ask": None, "mid": round(rates.get("USD", 0), 4)},
            "EURCNY": {"bid": None, "ask": None, "mid": round(rates.get("EUR", 0), 4)},
            "HKDCNY": {"bid": None, "ask": None, "mid": round(rates.get("HKD", 0), 4)},
            "JPYCNY": {"bid": None, "ask": None, "mid": round(rates.get("JPY", 0) / 100, 6)},
        }
    except Exception as e:
        print(f"API fetch error: {e}")
        return None


def fetch_all_quotes():
    """主入口：获取所有货币对的报价"""
    result = fetch_exchangerate_api()
    if result:
        return result

    print("All data sources failed")
    return None
```

- [ ] **Step 2: 验证 fetcher 可运行**

Run: `python -c "from fetcher import fetch_all_quotes; q = fetch_all_quotes(); print(q)"`
Expected: 打印汇率数据或 None（如果没有网络）

- [ ] **Step 3: Commit**

```bash
git add fetcher.py
git commit -m "feat: data fetcher module with free exchange rate API"
```

---

### Task 5: 报价条组件 — ui/quote_bar.py

**Files:**
- Create: `forex-monitor/ui/quote_bar.py`

- [ ] **Step 1: 创建报价条 widget**

```python
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class PairWidget(QWidget):
    """单个货币对的报价显示（买价 / 中间价 / 卖价）"""

    def __init__(self, pair_name):
        super().__init__()
        self.pair_name = pair_name
        layout = QVBoxLayout()
        layout.setSpacing(2)
        layout.setContentsMargins(12, 6, 12, 6)

        self.name_label = QLabel(pair_name)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setStyleSheet("color: #888; font-size: 11px;")

        self.mid_label = QLabel("--")
        self.mid_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mid_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #4ade80;")

        self.spread_label = QLabel("买 --  卖 --")
        self.spread_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spread_label.setStyleSheet("color: #666; font-size: 11px;")

        layout.addWidget(self.name_label)
        layout.addWidget(self.mid_label)
        layout.addWidget(self.spread_label)
        self.setLayout(layout)
        self.setStyleSheet("background: #0f3460; border-radius: 4px;")

    def update_quote(self, bid, ask, mid):
        self.mid_label.setText(f"{mid:.4f}")
        self.spread_label.setText(f"买 {bid:.4f}  卖 {ask:.4f}")


class QuoteBar(QWidget):
    """顶部浮动报价条，显示所有货币对"""

    def __init__(self):
        super().__init__()
        layout = QHBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(8, 4, 8, 4)

        self.pair_widgets = {}
        for pair in ["USDCNY", "EURCNY", "HKDCNY", "JPYCNY"]:
            w = PairWidget(pair)
            self.pair_widgets[pair] = w
            layout.addWidget(w)

        self.setLayout(layout)
        self.setStyleSheet("background: #0f3460;")

    def update_all(self, quotes):
        """quotes: dict {pair: {bid, ask, mid}}"""
        for pair, data in quotes.items():
            if pair in self.pair_widgets:
                bid = data.get("bid") or data["mid"]
                ask = data.get("ask") or data["mid"]
                self.pair_widgets[pair].update_quote(bid, ask, data["mid"])
```

- [ ] **Step 2: Commit**

```bash
git add ui/quote_bar.py
git commit -m "feat: floating quote bar widget with pair display"
```

---

### Task 6: 对比面板 — ui/compare_panel.py

**Files:**
- Create: `forex-monitor/ui/compare_panel.py`

- [ ] **Step 1: 创建 compare_panel.py（表格 + 买入/卖出切换 + 录入表单）**

```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QComboBox, QLineEdit, QLabel, QHeaderView, QFrame, QGroupBox
)
from PyQt6.QtCore import Qt
from calculator import compute_entry_result, market_cost_price


class ComparePanel(QWidget):
    def __init__(self, db, calculator):
        super().__init__()
        self.db = db
        self.calculator = calculator
        self.current_direction = "买入价"  # 或 "卖出价"
        self.bank_quotes = {}  # 最新的银行报价数据

        layout = QVBoxLayout()
        layout.setSpacing(12)

        # 方向切换按钮
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("比较方向："))
        self.buy_btn = QPushButton("买入价")
        self.sell_btn = QPushButton("卖出价")
        self.buy_btn.setCheckable(True)
        self.sell_btn.setCheckable(True)
        self.buy_btn.setChecked(True)
        self.buy_btn.clicked.connect(lambda: self._switch_direction("买入价"))
        self.sell_btn.clicked.connect(lambda: self._switch_direction("卖出价"))
        dir_layout.addWidget(self.buy_btn)
        dir_layout.addWidget(self.sell_btn)
        dir_layout.addStretch()
        layout.addLayout(dir_layout)

        # 银行对比表格
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["货币对", "银行", "银行买价", "银行卖价", "市场成本", "赚取(bp)"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table, stretch=2)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #333;")
        layout.addWidget(line)

        # 用户录入区域
        entry_group = QGroupBox("录入报价")
        entry_layout = QHBoxLayout()

        self.pair_combo = QComboBox()
        self.pair_combo.addItems(["USDCNY", "EURCNY", "HKDCNY", "JPYCNY"])
        entry_layout.addWidget(self.pair_combo)

        self.bank_combo = QComboBox()
        self.bank_combo.addItems(["中国银行", "招商银行", "宁波银行", "杭州银行"])
        entry_layout.addWidget(self.bank_combo)

        self.dir_combo = QComboBox()
        self.dir_combo.addItems(["买入价", "卖出价"])
        entry_layout.addWidget(self.dir_combo)

        self.quote_input = QLineEdit()
        self.quote_input.setPlaceholderText("输入报价")
        entry_layout.addWidget(self.quote_input)

        submit_btn = QPushButton("录入")
        submit_btn.clicked.connect(self._submit_entry)
        entry_layout.addWidget(submit_btn)

        entry_group.setLayout(entry_layout)
        layout.addWidget(entry_group)

        # 结果显示
        self.result_label = QLabel("录入后显示计算结果")
        self.result_label.setStyleSheet("color: #888; padding: 8px; background: #16213e; border-radius: 4px;")
        layout.addWidget(self.result_label)

        # 最近录入记录
        self.recent_label = QLabel("最近录入：")
        layout.addWidget(self.recent_label)

        self.setLayout(layout)

    def _switch_direction(self, direction):
        self.current_direction = direction
        self.buy_btn.setChecked(direction == "买入价")
        self.sell_btn.setChecked(direction == "卖出价")
        self._refresh_table()

    def update_bank_data(self, bank_quotes):
        """更新银行报价数据并刷新表格"""
        self.bank_quotes = bank_quotes
        self._refresh_table()

    def _refresh_table(self):
        self.table.setRowCount(0)
        market = self.calculator.get_latest_market_quotes()
        if not market:
            return

        # 模拟银行数据（实际应由 fetcher 提供）
        sample_data = [
            ("USDCNY", "中国银行", 7.2390, 7.2490),
            ("USDCNY", "招商银行", 7.2395, 7.2485),
            ("USDCNY", "宁波银行", 7.2400, 7.2480),
            ("USDCNY", "杭州银行", 7.2385, 7.2495),
            ("EURCNY", "中国银行", 7.8480, 7.8580),
            ("HKDCNY", "中国银行", 0.9240, 0.9280),
            ("JPYCNY", "中国银行", 0.0483, 0.0487),
        ]

        for pair, bank, bid, ask in sample_data:
            market_bid = market.get(pair, {}).get("bid", 0)
            market_ask = market.get(pair, {}).get("ask", 0)
            market_mid = market_cost_price(market_bid, market_ask) if (market_bid and market_ask) else market.get(pair, {}).get("mid", 0)

            quote = bid if self.current_direction == "买入价" else ask
            bp = round((quote - market_mid) / market_mid * 10000, 1) if market_mid else 0

            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(pair))
            self.table.setItem(row, 1, QTableWidgetItem(bank))
            self.table.setItem(row, 2, QTableWidgetItem(f"{bid:.4f}"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{ask:.4f}"))
            self.table.setItem(row, 4, QTableWidgetItem(f"{market_mid:.4f}"))
            item = QTableWidgetItem(f"{bp:+.1f}bp")
            item.setForeground(Qt.GlobalColor.red if bp > 0 else Qt.GlobalColor.darkGreen)
            self.table.setItem(row, 5, item)

    def _submit_entry(self):
        try:
            pair = self.pair_combo.currentText()
            bank = self.bank_combo.currentText()
            direction = self.dir_combo.currentText()
            user_quote = float(self.quote_input.text())

            result = self.calculator.compute_entry(pair, user_quote, direction)
            if result:
                self.result_label.setText(
                    f"市场成本价 {result['market_cost']:.4f}，银行赚取 {result['bp_vs_market']:+.1f}bp  "
                    f"| 银行成本价 {result['bank_cost']:.4f}，银行赚取 {result['bp_vs_bank']:+.1f}bp"
                )
                self._refresh_recent()
        except ValueError:
            self.result_label.setText("请输入有效的报价数字")
        except Exception as e:
            self.result_label.setText(f"错误: {e}")

    def _refresh_recent(self):
        entries = self.db.get_recent_user_entries()
        texts = []
        for e in entries[-5:]:
            texts.append(f"{e[0][11:16]} {e[1]} {e[2]} {e[3]} {e[4]:.4f} → {e[7]:+.1f}bp")
        self.recent_label.setText("最近录入：\n" + "\n".join(texts) if texts else "暂无录入记录")
```

- [ ] **Step 2: Commit**

```bash
git add ui/compare_panel.py
git commit -m "feat: bank comparison panel with buy/sell toggle and inline quote entry"
```

---

### Task 7: 历史图表 — ui/chart_widget.py

**Files:**
- Create: `forex-monitor/ui/chart_widget.py`

- [ ] **Step 1: 创建 chart_widget.py**

```python
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QComboBox, QLabel
import pyqtgraph as pg


class ChartWidget(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db

        layout = QVBoxLayout()

        self.pair_selector = QComboBox()
        self.pair_selector.addItems(["USDCNY", "EURCNY", "HKDCNY", "JPYCNY"])
        self.pair_selector.currentTextChanged.connect(self._refresh_chart)
        layout.addWidget(self.pair_selector)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#1a1a2e")
        self.plot_widget.setLabel("left", "价格")
        self.plot_widget.setLabel("bottom", "时间")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        layout.addWidget(self.plot_widget)

        self.setLayout(layout)

    def refresh(self):
        self._refresh_chart()

    def _refresh_chart(self):
        pair = self.pair_selector.currentText()
        quotes = self.db.get_recent_market_quotes(pair, limit=100)
        if not quotes:
            return

        times = list(range(len(quotes)))
        mids = [q[3] for q in quotes]

        self.plot_widget.clear()
        self.plot_widget.plot(times, mids, pen=pg.mkPen(color="#4ade80", width=2))
```

- [ ] **Step 2: Commit**

```bash
git add ui/chart_widget.py
git commit -m "feat: historical chart widget with pyqtgraph"
```

---

### Task 8: 主窗口 — ui/main_window.py

**Files:**
- Create: `forex-monitor/ui/main_window.py`

- [ ] **Step 1: 创建 main_window.py**

```python
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QTabWidget, QLabel, QStatusBar
from PyQt6.QtCore import QTimer, QThread, pyqtSignal
from datetime import datetime
from config import CURRENCY_PAIRS, FETCH_INTERVAL_SECONDS
from database import Database
from calculator import compute_entry_result, market_cost_price
from fetcher import fetch_all_quotes
from ui.quote_bar import QuoteBar
from ui.compare_panel import ComparePanel
from ui.chart_widget import ChartWidget


class FetchWorker(QThread):
    finished = pyqtSignal(dict)

    def run(self):
        quotes = fetch_all_quotes()
        if quotes:
            self.finished.emit(quotes)


class CalculatorBridge:
    """连接 calculator 和 UI 的中间层"""

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

        # 没有银行数据时使用市场价模拟
        bank_bid = market_bid
        bank_ask = market_ask

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

        # 顶部报价条
        self.quote_bar = QuoteBar()
        layout.addWidget(self.quote_bar)

        # 标签页
        self.tabs = QTabWidget()
        self.compare_panel = ComparePanel(self.db, self.calculator)
        self.chart_widget = ChartWidget(self.db)

        self.tabs.addTab(self.compare_panel, "银行对比 + 录入")
        self.tabs.addTab(self.chart_widget, "历史图表")

        layout.addWidget(self.tabs)

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("就绪")
        self.status_bar.addWidget(self.status_label)

        # 定时刷新
        self.timer = QTimer()
        self.timer.timeout.connect(self._fetch_data)
        self.timer.start(FETCH_INTERVAL_SECONDS * 1000)

        # 立即拉一次数据
        self._fetch_data()

    def _fetch_data(self):
        self.status_label.setText("正在获取数据...")
        self.worker = FetchWorker()
        self.worker.finished.connect(self._on_data_fetched)
        self.worker.start()

    def _on_data_fetched(self, quotes):
        self.calculator.set_market_quotes(quotes)
        self.quote_bar.update_all(quotes)
        self.compare_panel.update_bank_data(quotes)
        self.chart_widget.refresh()
        self.status_label.setText(f"最后更新: {datetime.now().strftime('%H:%M:%S')}")
```

- [ ] **Step 2: Commit**

```bash
git add ui/main_window.py
git commit -m "feat: main window with quote bar, tabs, auto-refresh timer"
```

---

### Task 9: 集成验证 — 运行并测试

- [ ] **Step 1: 安装依赖**

Run: `pip install -r requirements.txt`

- [ ] **Step 2: 启动程序**

Run: `python main.py`
Expected: 窗口弹出，显示实时汇率数据，报价条每 60 秒刷新

- [ ] **Step 3: 测试录入功能**

操作：选择 USDCNY → 中国银行 → 买入价 → 输入 7.2480 → 点击"录入"
Expected: 下方显示市场成本价和赚取的 bp

- [ ] **Step 4: 验证数据持久化**

关闭程序 → 重新运行
Expected：历史图表显示之前的数据，最近录入记录保留

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: full integration of forex monitor app"
```
