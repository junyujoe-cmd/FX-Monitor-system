from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QDateEdit
from PyQt6.QtCore import Qt, QDate
from datetime import datetime
import pyqtgraph as pg
from config import BANK_SPREADS


LINE_CONFIG = [
    {"name": "银行买价", "color": "#22c55e", "width": 1.5, "style": None},
    {"name": "银行卖价", "color": "#ef4444", "width": 1.5, "style": None},
    {"name": "市场成本", "color": "#9ca3af", "width": 1.5, "style": None},
    {"name": "银行成本", "color": "#f59e0b", "width": 1.5, "style": Qt.PenStyle.DashLine},
]


def bank_cost_from_row(r):
    if r[2] is not None and r[3] is not None:
        return round((r[2] + r[3]) / 2, 4)
    return r[1]


class ChartWidget(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.current_data = None
        self._chart_timestamps = []

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
        selector_row.addSpacing(10)
        selector_row.addWidget(QLabel("日期:"))
        self.date_picker = QDateEdit()
        self.date_picker.setDate(QDate.currentDate())
        self.date_picker.setCalendarPopup(True)
        self.date_picker.setDisplayFormat("yyyy-MM-dd")
        self.date_picker.setStyleSheet("""
            QDateEdit { color: #ccc; background: #16213e; padding: 2px 6px;
                        border: 1px solid #444; border-radius: 3px; font-size: 12px; }
            QDateEdit::drop-down { border: none; }
            QDateEdit::down-arrow { image: none; }
        """)
        self.date_picker.dateChanged.connect(self._refresh_chart)
        selector_row.addWidget(self.date_picker)
        selector_row.addStretch()
        layout.addLayout(selector_row)

        self.plot_widget = pg.PlotWidget(axisItems={"bottom": pg.DateAxisItem()})
        self.plot_widget.setBackground("#1a1a2e")
        self.plot_widget.setLabel("left", "价格")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        layout.addWidget(self.plot_widget)

        self.v_line = pg.InfiniteLine(angle=90, movable=False,
                                       pen=pg.mkPen("#ffffff", width=1, style=Qt.PenStyle.DashLine))
        self.v_line.setVisible(False)
        self.plot_widget.addItem(self.v_line)

        self.info_text = pg.TextItem()
        self.info_text.setVisible(False)
        self.plot_widget.addItem(self.info_text)

        self.legend = self.plot_widget.addLegend(offset=(1, 0))

        self.plot_widget.scene().sigMouseMoved.connect(self._on_mouse_moved)

        self.setLayout(layout)

    def refresh(self):
        self._refresh_chart()

    def _refresh_chart(self):
        pair = self.pair_selector.currentText()
        bank = self.bank_selector.currentText()
        spread = BANK_SPREADS.get(bank, {"bid_offset": 0, "ask_offset": 0})

        selected_date = self.date_picker.date().toString("yyyy-MM-dd")
        today_str = datetime.now().strftime("%Y-%m-%d")
        is_today = selected_date == today_str

        if is_today:
            data = self.db.get_chart_data(pair, bank, limit=240)
        else:
            data = self.db.get_chart_data_by_date(pair, bank, selected_date)

        self.current_data = data
        if not data:
            self.plot_widget.clear()
            self.plot_widget.addItem(self.v_line)
            self.plot_widget.addItem(self.info_text)
            self.v_line.setVisible(False)
            self.info_text.setVisible(False)
            return

        self._chart_timestamps = [datetime.fromisoformat(r[0]).timestamp() for r in data]
        times = self._chart_timestamps
        mids = [r[1] for r in data]
        bids = [r[2] if r[2] is not None else round(r[1] + spread["bid_offset"], 4) for r in data]
        asks = [r[3] if r[3] is not None else round(r[1] + spread["ask_offset"], 4) for r in data]
        costs = [round((bids[i] + asks[i]) / 2, 4) for i in range(len(data))]

        self.plot_widget.clear()
        self.legend = self.plot_widget.addLegend(offset=(1, 0))

        y_vals = [bids, asks, mids, costs]
        for i, y in enumerate(y_vals):
            cfg = LINE_CONFIG[i]
            pen_kw = {"color": cfg["color"], "width": cfg["width"]}
            if cfg["style"] is not None:
                pen_kw["style"] = cfg["style"]
            pen = pg.mkPen(**pen_kw)
            self.plot_widget.plot(times, y, pen=pen, name=cfg["name"],
                                  symbol="o", symbolSize=3, symbolBrush=cfg["color"])

        self.plot_widget.addItem(self.v_line)
        self.plot_widget.addItem(self.info_text)
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
        timestamps = self._chart_timestamps
        if not timestamps:
            return
        idx = min(range(len(timestamps)), key=lambda i: abs(timestamps[i] - x))

        self.v_line.setPos(timestamps[idx])
        self.v_line.setVisible(True)

        ts = data[idx][0][11:19]
        mm = data[idx][1]
        spread = BANK_SPREADS.get(self.bank_selector.currentText(), {"bid_offset": 0, "ask_offset": 0})
        bb = data[idx][2] if data[idx][2] is not None else round(data[idx][1] + spread["bid_offset"], 4)
        ba = data[idx][3] if data[idx][3] is not None else round(data[idx][1] + spread["ask_offset"], 4)
        bc = round((bb + ba) / 2, 4)

        max_val = max(mm, bb, ba, bc)
        min_val = min(mm, bb, ba, bc)
        view = self.plot_widget.plotItem.vb
        view_range = view.viewRange()
        mid_x = (view_range[0][0] + view_range[0][1]) / 2
        anchor = (1, 0) if timestamps[idx] > mid_x else (0, 0)
        self.info_text.setAnchor(anchor)
        self.info_text.setPos(timestamps[idx], max_val if anchor[0] == 0 else max_val)
        self.info_text.setHtml(f"""
        <div style="background:#1a1a2e; color:#ccc; padding:6px; border:1px solid #444; border-radius:4px; font-size:11px;">
          <div>{ts}</div>
          <div><span style="color:#22c55e">银行买价</span> {bb:.4f}</div>
          <div><span style="color:#ef4444">银行卖价</span> {ba:.4f}</div>
          <div><span style="color:#9ca3af">市场成本</span> {mm:.4f}</div>
          <div><span style="color:#f59e0b">银行成本</span> {bc:.4f}</div>
        </div>
        """)
        self.info_text.setVisible(True)
