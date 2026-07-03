"""
技术指标信号页面 — RSI / MACD / 布林带
"""

from PySide6.QtCore import QAbstractTableModel, QSortFilterProxyModel, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from signals.technical import TechnicalSignal, compute_technical

LEVEL_COLORS = {
    "强烈": QColor("#b71c1c"),
    "轻度": QColor("#f57f17"),
    "无": QColor("#2e7d32"),
}

INDICATOR_NAMES = {
    "RSI": "相对强弱指标",
    "MACD": "异同移动平均",
    "BB": "布林带",
}


class TechnicalTableModel(QAbstractTableModel):
    """技术信号数据模型"""

    HEADERS = ["物品名", "区域", "指标", "指标值", "信号描述", "等级"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: list[TechnicalSignal] = []

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
            s.item_name,
            s.hub_name,
            INDICATOR_NAMES.get(s.indicator, s.indicator),
            f"{s.value:.1f}" if s.indicator != "MACD" else f"{s.value:.3f}",
            s.signal,
            s.level,
        ]
        if role == Qt.DisplayRole:
            return cols[index.column()] if index.column() < len(cols) else ""
        if role == Qt.BackgroundRole and index.column() == 5:
            return LEVEL_COLORS.get(s.level)
        if role == Qt.ForegroundRole and index.column() == 5:
            return QColor(Qt.white)
        return None

    def set_data(self, data: list[TechnicalSignal]):
        self.beginResetModel()
        self._data = data
        self.endResetModel()


class TechnicalPage(QWidget):
    """技术指标信号页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # 过滤栏
        toolbar = QHBoxLayout()

        toolbar.addWidget(QLabel("筛选指标:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部", "RSI", "MACD", "BB"])
        self.filter_combo.currentTextChanged.connect(self._apply_filter)
        toolbar.addWidget(self.filter_combo)

        self.refresh_btn = QPushButton("刷新技术指标")
        self.refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(self.refresh_btn)

        self.count_label = QLabel("共 0 个信号")
        toolbar.addWidget(self.count_label)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 表格
        self.model = TechnicalTableModel()
        self.proxy = QSortFilterProxyModel()
        self.proxy.setSourceModel(self.model)

        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        layout.addWidget(self.table)

    def refresh(self):
        signals = compute_technical()
        self.model.set_data(signals)
        self._apply_filter()
        self.count_label.setText(f"共 {len(signals)} 个信号")

    def _apply_filter(self):
        indicator = self.filter_combo.currentText()
        if indicator == "全部":
            self.proxy.setFilterFixedString("")
            self.proxy.setFilterKeyColumn(-1)
        else:
            self.proxy.setFilterFixedString(indicator)
            self.proxy.setFilterKeyColumn(2)
