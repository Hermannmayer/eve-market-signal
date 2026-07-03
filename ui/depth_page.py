"""
深度不平衡信号页面 — 显示每个监控目标的当前不平衡比率 + 趋势图
"""

from PySide6.QtCore import QAbstractTableModel, QSortFilterProxyModel, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QHBoxLayout, QHeaderView, QLabel, QPushButton, QTableView, QVBoxLayout, QWidget

from signals.depth import DepthSignal, compute_depth

LEVEL_COLORS = {
    "强烈": QColor("#b71c1c"),
    "轻度": QColor("#f57f17"),
    "无": QColor("#2e7d32"),
}

DIRECTION_MARKERS = {
    "看涨": "▲",
    "看跌": "▼",
}


class DepthTableModel(QAbstractTableModel):
    """深度信号数据模型"""

    HEADERS = ["物品名", "区域", "不平衡比率", "历史均值", "偏离σ", "方向", "信号等级"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: list[DepthSignal] = []

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self.HEADERS)

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEADERS[section]
        return None

    def data(self, index, role):
        if not index.isValid():
            return None
        s = self._data[index.row()]
        marker = DIRECTION_MARKERS.get(s.direction, "")
        cols = [
            s.item_name, s.hub_name,
            f"{s.current_imbalance:.3f}",
            f"{s.historical_mean:.3f}",
            f"{s.deviation_sigma:.2f}",
            f"{marker} {s.direction}",
            s.signal_level,
        ]
        if role == Qt.DisplayRole:
            return cols[index.column()] if index.column() < len(cols) else ""
        if role == Qt.BackgroundRole and index.column() == 6:
            return LEVEL_COLORS.get(s.signal_level)
        if role == Qt.ForegroundRole and index.column() == 6:
            return QColor(Qt.white)
        return None

    def set_data(self, data: list[DepthSignal]):
        self.beginResetModel()
        self._data = data
        self.endResetModel()


class DepthPage(QWidget):
    """深度不平衡页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        self.refresh_btn = QPushButton("刷新深度")
        self.refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(self.refresh_btn)
        self.count_label = QLabel("共 0 个信号")
        toolbar.addWidget(self.count_label)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.model = DepthTableModel()
        self.proxy = QSortFilterProxyModel()
        self.proxy.setSourceModel(self.model)

        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        layout.addWidget(self.table)

    def refresh(self):
        signals = compute_depth()
        self.model.set_data(signals)
        self.count_label.setText(f"共 {len(signals)} 个信号")
