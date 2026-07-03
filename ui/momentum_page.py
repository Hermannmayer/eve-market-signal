"""
趋势信号列表页面
"""

from PySide6.QtCore import QAbstractTableModel, QSortFilterProxyModel, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QHBoxLayout, QHeaderView, QLabel, QPushButton, QTableView, QVBoxLayout, QWidget

from signals.momentum import MomentumSignal, compute_momentum

# 信号标签 → 背景色
LABEL_COLORS = {
    "放量上涨": QColor("#1b5e20"),   # 深绿
    "放量下跌": QColor("#b71c1c"),   # 深红
    "缩量阴跌": QColor("#e65100"),   # 橙色
    "无量上涨": QColor("#f57f17"),   # 金黄
}


class MomentumTableModel(QAbstractTableModel):
    """趋势信号数据模型"""

    HEADERS = ["物品名", "区域", "信号", "量比", "价比", "近7日均量", "近30日均量"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: list[MomentumSignal] = []

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
        cols = [
            s.item_name, s.hub_name, s.label,
            f"{s.volume_ratio:.2f}", f"{s.price_ratio:.2f}",
            f"{s.avg_volume_7d:,.0f}", f"{s.avg_volume_30d:,.0f}",
        ]
        if role == Qt.DisplayRole:
            return cols[index.column()] if index.column() < len(cols) else ""
        if role == Qt.BackgroundRole and index.column() == 2:
            return LABEL_COLORS.get(s.label)
        if role == Qt.ForegroundRole and index.column() == 2:
            return QColor(Qt.white)
        return None

    def set_data(self, data: list[MomentumSignal]):
        self.beginResetModel()
        self._data = data
        self.endResetModel()


class MomentumPage(QWidget):
    """趋势信号页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        self.refresh_btn = QPushButton("刷新趋势")
        self.refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(self.refresh_btn)
        self.count_label = QLabel("共 0 个信号")
        toolbar.addWidget(self.count_label)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.model = MomentumTableModel()
        self.proxy = QSortFilterProxyModel()
        self.proxy.setSourceModel(self.model)

        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        layout.addWidget(self.table)

    def refresh(self):
        signals = compute_momentum()
        self.model.set_data(signals)
        self.count_label.setText(f"共 {len(signals)} 个信号")
