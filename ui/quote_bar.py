from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt


class PairWidget(QWidget):
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
        for pair, data in quotes.items():
            if pair in self.pair_widgets:
                bid = data.get("bid") or data["mid"]
                ask = data.get("ask") or data["mid"]
                self.pair_widgets[pair].update_quote(bid, ask, data["mid"])
