from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QComboBox, QLineEdit, QLabel, QHeaderView, QFrame, QGroupBox
)
from PyQt6.QtCore import Qt
from calculator import market_cost_price


BANK_SPREADS = {
    "中国银行": {"bid_offset": -0.0020, "ask_offset": 0.0020},
    "招商银行": {"bid_offset": -0.0015, "ask_offset": 0.0015},
    "宁波银行": {"bid_offset": -0.0010, "ask_offset": 0.0010},
    "杭州银行": {"bid_offset": -0.0018, "ask_offset": 0.0018},
}


class ComparePanel(QWidget):
    def __init__(self, db, calculator):
        super().__init__()
        self.db = db
        self.calculator = calculator
        self.current_direction = "买入价"
        self.latest_quotes = {}

        layout = QVBoxLayout()
        layout.setSpacing(12)

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

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["货币对", "银行", "银行买价", "银行卖价", "市场成本", "赚取(bp)"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table, stretch=2)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #333;")
        layout.addWidget(line)

        entry_group = QGroupBox("录入报价")
        entry_layout = QHBoxLayout()

        self.pair_combo = QComboBox()
        self.pair_combo.addItems(["USDCNY", "EURCNY", "HKDCNY", "JPYCNY"])
        entry_layout.addWidget(self.pair_combo)

        self.bank_combo = QComboBox()
        self.bank_combo.addItems(list(BANK_SPREADS.keys()))
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

        self.result_label = QLabel("录入后显示计算结果")
        self.result_label.setStyleSheet("color: #888; padding: 8px; background: #16213e; border-radius: 4px;")
        layout.addWidget(self.result_label)

        self.recent_label = QLabel("最近录入：")
        layout.addWidget(self.recent_label)

        self.setLayout(layout)

    def _switch_direction(self, direction):
        self.current_direction = direction
        self.buy_btn.setChecked(direction == "买入价")
        self.sell_btn.setChecked(direction == "卖出价")
        self._refresh_table()

    def update_bank_data(self, quotes):
        self.latest_quotes = quotes
        self._refresh_table()

    def _simulate_bank_data(self):
        rows = []
        for pair, market in self.latest_quotes.items():
            mid = market["mid"]
            for bank, spread in BANK_SPREADS.items():
                bid = round(mid + spread["bid_offset"], 4)
                ask = round(mid + spread["ask_offset"], 4)
                rows.append((pair, bank, bid, ask))
        return rows

    def _refresh_table(self):
        self.table.setRowCount(0)
        if not self.latest_quotes:
            return

        bank_rows = self._simulate_bank_data()

        for pair, bank, bid, ask in bank_rows:
            market = self.latest_quotes.get(pair, {})
            market_mid = market.get("mid", 0)
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
