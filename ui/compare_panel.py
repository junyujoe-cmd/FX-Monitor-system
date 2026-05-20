from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QLineEdit, QLabel, QGroupBox
)
from config import BANK_SPREADS


class ComparePanel(QWidget):
    def __init__(self, db, calculator):
        super().__init__()
        self.db = db
        self.calculator = calculator
        self.latest_quotes = {}

        layout = QVBoxLayout()
        layout.setSpacing(12)

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

        layout.addStretch()
        self.setLayout(layout)

    def update_bank_data(self, quotes):
        self.latest_quotes = quotes

    def _submit_entry(self):
        try:
            pair = self.pair_combo.currentText()
            bank = self.bank_combo.currentText()
            direction = self.dir_combo.currentText()
            user_quote = float(self.quote_input.text())

            market = self.latest_quotes.get(pair, {})
            market_mid = market.get("mid", 0)
            if not market_mid:
                self.result_label.setText("暂无市场数据，请等待报价刷新")
                return

            spread = BANK_SPREADS.get(bank, {"bid_offset": 0, "ask_offset": 0})
            bank_bid = round(market_mid + spread["bid_offset"], 4)
            bank_ask = round(market_mid + spread["ask_offset"], 4)
            bank_cost = round((bank_bid + bank_ask) / 2, 4)

            if direction == "买入价":
                bp_vs_bank = round((bank_cost - user_quote) * 10000, 1)
                bp_vs_market = round((market_mid - user_quote) * 10000, 1)
                formula_bank = f"({bank_cost:.4f} - {user_quote:.4f}) × 10000 = {bp_vs_bank:.1f}bp"
                formula_market = f"({market_mid:.4f} - {user_quote:.4f}) × 10000 = {bp_vs_market:.1f}bp"
            else:
                bp_vs_bank = round((user_quote - bank_cost) * 10000, 1)
                bp_vs_market = round((user_quote - market_mid) * 10000, 1)
                formula_bank = f"({user_quote:.4f} - {bank_cost:.4f}) × 10000 = {bp_vs_bank:.1f}bp"
                formula_market = f"({user_quote:.4f} - {market_mid:.4f}) × 10000 = {bp_vs_market:.1f}bp"

            self.db.save_user_entry(
                pair=pair, bank=bank, direction=direction,
                user_quote=user_quote,
                market_cost=market_mid,
                bank_cost=bank_cost,
                bp_vs_market=bp_vs_market,
                bp_vs_bank=bp_vs_bank,
            )

            self.result_label.setText(
                f"▎对比市场中间价\n"
                f"  公式: {formula_market}\n"
                f"  结论: 银行赚取 {bp_vs_market:.1f}bp\n\n"
                f"▎对比{bank}自身成本\n"
                f"  公式: {formula_bank}\n"
                f"  结论: 银行赚取 {bp_vs_bank:.1f}bp"
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
            texts.append(f"{e[0][11:16]} {e[1]} {e[2]} {e[3]} {e[4]:.4f} → 银行赚 {e[7]:.1f}bp")
        self.recent_label.setText("最近录入：\n" + "\n".join(texts) if texts else "暂无录入记录")
