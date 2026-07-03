"""
价差信号表格页面
"""

from PySide6.QtCore import QAbstractTableModel, QSortFilterProxyModel, Qt
from PySide6.QtWidgets import QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton, QTableView, QVBoxLayout, QWidget

from signals.spread import SpreadSignal, compute_spreads


class SpreadTableModel(QAbstractTableModel):
    """价差信号数据模型"""

    HEADERS = [
        "物品名", "买入区域", "卖出区域", "买入价",
        "卖出价", "单件利润", "利润率%", "可交易量", "总利润",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: list[SpreadSignal] = []

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self.HEADERS)

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEADERS[section]
        return None

    def data(self, index, role):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        s = self._data[index.row()]
        cols = [
            s.item_name, s.buy_hub, s.sell_hub,
            f"{s.buy_price:,.2f}", f"{s.sell_price:,.2f}",
            f"{s.per_unit_profit:,.2f}", f"{s.profit_margin:.1f}",
            f"{s.trade_volume:,}", f"{s.total_profit:,.2f}",
        ]
        return cols[index.column()] if index.column() < len(cols) else ""

    def set_data(self, data: list[SpreadSignal]):
        self.beginResetModel()
        self._data = data
        self.endResetModel()


class SpreadPage(QWidget):
    """价差信号页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # 过滤栏
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("最低利润率 (%):"))
        self.min_margin_input = QLineEdit("10")
        filter_layout.addWidget(self.min_margin_input)

        self.refresh_btn = QPushButton("刷新价差")
        self.refresh_btn.clicked.connect(self.refresh)
        filter_layout.addWidget(self.refresh_btn)

        self.count_label = QLabel("共 0 个机会")
        filter_layout.addWidget(self.count_label)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # 表格
        self.model = SpreadTableModel()
        self.proxy = QSortFilterProxyModel()
        self.proxy.setSourceModel(self.model)

        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        layout.addWidget(self.table)

    def refresh(self):
        min_margin = float(self.min_margin_input.text().strip() or "10")
        signals = compute_spreads(min_margin=min_margin)
        self.model.set_data(signals)
        self.count_label.setText(f"共 {len(signals)} 个机会")
