from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt
from config import BANK_SPREADS, CURRENCY_PAIRS


class PairWidget(QWidget):
    def __init__(self, pair_name):
        super().__init__()
        self.pair_name = pair_name
        layout = QVBoxLayout()
        layout.setSpacing(2)
        layout.setContentsMargins(10, 6, 10, 6)

        self.name_label = QLabel(pair_name)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setStyleSheet("color: #888; font-size: 10px;")

        mid_row = QHBoxLayout()
        mid_row.setSpacing(8)
        self.buy_label = QLabel("买 --")
        self.buy_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.buy_label.setStyleSheet("color: #4ade80; font-weight: bold; font-size: 15px;")
        self.sell_label = QLabel("卖 --")
        self.sell_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sell_label.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 15px;")
        mid_row.addWidget(self.buy_label)
        mid_row.addWidget(self.sell_label)

        self.cost_label = QLabel("市场 --  银行 --")
        self.cost_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cost_label.setStyleSheet("color: #666; font-size: 10px;")

        layout.addWidget(self.name_label)
        layout.addLayout(mid_row)
        layout.addWidget(self.cost_label)
        self.setLayout(layout)
        self.setStyleSheet("background: #0f3460; border-radius: 4px;")

    def update_quote(self, bid, ask, market_cost, bank_cost):
        self.buy_label.setText(f"买 {bid:.4f}")
        self.sell_label.setText(f"卖 {ask:.4f}")
        self.cost_label.setText(f"市场 {market_cost:.4f}  银行 {bank_cost:.4f}")


class SourceRow(QWidget):
    def __init__(self, source_name):
        super().__init__()
        layout = QHBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(4, 2, 4, 2)

        name_label = QLabel(source_name)
        name_label.setFixedWidth(56)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")
        layout.addWidget(name_label)

        self.widgets = {}
        for pair in CURRENCY_PAIRS:
            w = PairWidget(pair)
            self.widgets[pair] = w
            layout.addWidget(w)

        self.setLayout(layout)

    def update_pair(self, pair, bid, ask, market_cost, bank_cost):
        if pair in self.widgets:
            self.widgets[pair].update_quote(bid, ask, market_cost, bank_cost)


class QuoteBar(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setSpacing(2)
        layout.setContentsMargins(4, 4, 4, 4)

        self.sources = {}
        for name in ["CFETS", "中国银行", "招商银行"]:
            row = SourceRow(name)
            self.sources[name] = row
            layout.addWidget(row)

        self.setLayout(layout)
        self.setStyleSheet("background: #0a1628;")

    def update_all(self, quotes, bank_quotes=None):
        for pair, data in quotes.items():
            mid = data["mid"]
            bid = data.get("bid") if data.get("bid") is not None else mid
            ask = data.get("ask") if data.get("ask") is not None else mid
            row = self.sources.get("CFETS")
            if row:
                row.update_pair(pair, bid, ask, mid, mid)

        for bank, spread in BANK_SPREADS.items():
            row = self.sources.get(bank)
            if not row:
                continue
            for pair, data in quotes.items():
                mid = data["mid"]
                if bank_quotes and bank in bank_quotes and pair in bank_quotes[bank]:
                    r = bank_quotes[bank][pair]
                    bid, ask = r["bid"], r["ask"]
                else:
                    bid = round(mid + spread["bid_offset"], 4)
                    ask = round(mid + spread["ask_offset"], 4)
                bank_cost = round((bid + ask) / 2, 4)
                row.update_pair(pair, bid, ask, mid, bank_cost)
