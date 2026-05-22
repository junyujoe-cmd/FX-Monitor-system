from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel
from PyQt6.QtCore import Qt
from datetime import datetime
import pyqtgraph as pg
from config import BANK_SPREADS


LINE_CONFIG = [
    {"name": "银行卖价", "color": "#ef4444", "width": 1.5, "style": None},
    {"name": "银行成本", "color": "#f59e0b", "width": 1.5, "style": Qt.PenStyle.DashLine},
    {"name": "市场成本", "color": "#9ca3af", "width": 1.5, "style": None},
    {"name": "银行买价", "color": "#22c55e", "width": 1.5, "style": None},
]


class ChartWidget(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.current_data = None
        self._chart_timestamps = []
        self._nine_am_ts = 0

        layout = QVBoxLayout()
        layout.setSpacing(8)

        selector_row = QHBoxLayout()
        selector_row.addWidget(QLabel("货币对:"))
        self.pair_selector = QComboBox()
        self.pair_selector.addItems(["USDCNY", "EURCNY", "HKDCNY", "JPYCNY"])
        self.pair_selector.currentTextChanged.connect(self._refresh_chart)
        selector_row.addWidget(self.pair_selector)
        selector_row.addSpacing(10)
        selector_row.addWidget(QLabel("银行:"))
        self.bank_selector = QComboBox()
        self.bank_selector.addItems(list(BANK_SPREADS.keys()))
        self.bank_selector.currentTextChanged.connect(self._refresh_chart)
        selector_row.addWidget(self.bank_selector)
        selector_row.addStretch()
        layout.addLayout(selector_row)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#1a1a2e")
        self.plot_widget.setLabel("left", "价格")
        self.plot_widget.setLabel("bottom", "时间")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.plotItem.vb.setMouseEnabled(x=False, y=False)
        layout.addWidget(self.plot_widget)

        self.v_line = pg.InfiniteLine(angle=90, movable=False,
                                       pen=pg.mkPen("#ffffff", width=1, style=Qt.PenStyle.DashLine))
        self.v_line.setVisible(False)
        self.v_line.setZValue(100)
        self.plot_widget.addItem(self.v_line)

        self.info_text = pg.TextItem()
        self.info_text.setVisible(False)
        self.info_text.setZValue(100)
        self.plot_widget.addItem(self.info_text)

        self.plot_widget.scene().sigMouseMoved.connect(self._on_mouse_moved)

        self.setLayout(layout)

    def refresh(self):
        self._refresh_chart()

    def _refresh_chart(self):
        pair = self.pair_selector.currentText()
        bank = self.bank_selector.currentText()
        spread = BANK_SPREADS.get(bank, {"bid_offset": 0, "ask_offset": 0})

        data = self.db.get_chart_data(pair, bank)
        self.current_data = data
        if not data:
            self.plot_widget.plotItem.clear()
            return

        self._chart_timestamps = [float(datetime.fromisoformat(r[0]).timestamp()) for r in data]
        self._nine_am_ts = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0).timestamp()
        times = [(t - self._nine_am_ts) / 60 for t in self._chart_timestamps]

        mids = [float(r[1]) for r in data]
        bids = [float(r[2]) if r[2] is not None else float(round(float(r[1]) + spread["bid_offset"], 4)) for r in data]
        asks = [float(r[3]) if r[3] is not None else float(round(float(r[1]) + spread["ask_offset"], 4)) for r in data]
        costs = [float(round((bids[i] + asks[i]) / 2, 4)) for i in range(len(data))]

        self.plot_widget.plotItem.clearPlots()
        self.plot_widget.plotItem.legend = None

        y_vals = [asks, costs, mids, bids]
        for i, y in enumerate(y_vals):
            cfg = LINE_CONFIG[i]
            pen = pg.mkPen(color=cfg["color"], width=cfg["width"],
                           style=cfg["style"] if cfg["style"] is not None else Qt.PenStyle.SolidLine)
            self.plot_widget.plot(times, y, pen=pen, name=cfg["name"],
                                  symbol="o", symbolSize=3, symbolBrush=cfg["color"])

        self.plot_widget.addLegend(offset=(1, 0))
        self.plot_widget.setXRange(0, 450, padding=0)

        tick_pos = []
        tick_labels = []
        for m in range(0, 451, 30):
            tick_pos.append(m)
            h = 9 + m // 60
            minute = m % 60
            tick_labels.append(f"{h:02d}:{minute:02d}")
        self.plot_widget.getAxis("bottom").setTicks([list(zip(tick_pos, tick_labels))])

        ref_price = float(mids[0])
        margins = {"USDCNY": 0.03, "EURCNY": 0.05, "HKDCNY": 0.005, "JPYCNY": 0.05}
        margin = margins.get(pair, 0.03)
        self.plot_widget.setYRange(ref_price - margin, ref_price + margin, padding=0)

        self.v_line.setVisible(False)
        self.info_text.setVisible(False)

    def _on_mouse_moved(self, pos):
        if not self.current_data:
            self.v_line.setVisible(False)
            self.info_text.setVisible(False)
            return

        mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)
        x = mouse_point.x()

        data = self.current_data
        timestamps = [(t - self._nine_am_ts) / 60 for t in self._chart_timestamps]
        if not timestamps:
            return
        idx = min(range(len(timestamps)), key=lambda i: abs(timestamps[i] - x))

        self.v_line.setPos(timestamps[idx])
        self.v_line.setVisible(True)

        m = int(timestamps[idx])
        h = 9 + m // 60
        ts = f"{h:02d}:{m % 60:02d}"
        mm = data[idx][1]
        sp = BANK_SPREADS.get(self.bank_selector.currentText(), {"bid_offset": 0, "ask_offset": 0})
        bb = data[idx][2] if data[idx][2] is not None else round(data[idx][1] + sp["bid_offset"], 4)
        ba = data[idx][3] if data[idx][3] is not None else round(data[idx][1] + sp["ask_offset"], 4)
        bc = round((bb + ba) / 2, 4)

        max_val = max(mm, bb, ba, bc)
        view = self.plot_widget.plotItem.vb
        view_range = view.viewRange()
        mid_x = (view_range[0][0] + view_range[0][1]) / 2
        anchor = (1, 0) if timestamps[idx] > mid_x else (0, 0)
        self.info_text.setAnchor(anchor)
        self.info_text.setPos(timestamps[idx], max_val if anchor[0] == 0 else max_val)
        self.info_text.setHtml(f"""
        <div style="background:#1a1a2e; color:#ccc; padding:6px; border:1px solid #444; border-radius:4px; font-size:11px;">
          <div>{ts}</div>
          <div><span style="color:#ef4444">银行卖价</span> {ba:.4f}</div>
          <div><span style="color:#f59e0b">银行成本</span> {bc:.4f}</div>
          <div><span style="color:#9ca3af">市场成本</span> {mm:.4f}</div>
          <div><span style="color:#22c55e">银行买价</span> {bb:.4f}</div>
        </div>
        """)
        self.info_text.setVisible(True)
