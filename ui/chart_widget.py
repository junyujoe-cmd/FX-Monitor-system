from PyQt6.QtWidgets import QWidget, QVBoxLayout, QComboBox
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
