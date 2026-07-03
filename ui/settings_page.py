"""
监控目标 + 阈值配置页面
"""

from PySide6.QtCore import QAbstractTableModel, Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from signals.db import get_setting, get_signal_db, set_setting


class WatchTargetModel(QAbstractTableModel):
    """监控目标数据模型"""

    HEADERS = ["type_id", "区域ID", "标签", "启用"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: list[dict] = []

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
        row = self._data[index.row()]
        col = index.column()
        if role == Qt.DisplayRole:
            key = list(row.keys())[col] if col < len(row) else ""
            return str(row.get(key, ""))
        if role == Qt.CheckStateRole and col == 3:
            return Qt.Checked if row.get("enabled") else Qt.Unchecked
        return None

    def setData(self, index, value, role):
        if index.column() == 3 and role == Qt.CheckStateRole:
            tid = self._data[index.row()]["type_id"]
            rid = self._data[index.row()]["region_id"]
            enabled = 1 if value == Qt.Checked else 0
            conn = get_signal_db()
            conn.execute(
                "UPDATE watch_targets SET enabled = ? WHERE type_id = ? AND region_id = ?",
                (enabled, tid, rid),
            )
            conn.commit()
            self._data[index.row()]["enabled"] = enabled
            return True
        return False

    def flags(self, index):
        if index.column() == 3:
            return super().flags(index) | Qt.ItemIsUserCheckable
        return super().flags(index)

    def refresh(self):
        """从数据库重新加载"""
        conn = get_signal_db()
        rows = conn.execute(
            "SELECT type_id, region_id, label, enabled FROM watch_targets ORDER BY type_id"
        ).fetchall()
        self.beginResetModel()
        self._data = [
            {"type_id": r["type_id"], "region_id": r["region_id"],
             "label": r["label"] or "", "enabled": r["enabled"]}
            for r in rows
        ]
        self.endResetModel()

    def remove_row(self, row: int):
        """删除一行"""
        if 0 <= row < len(self._data):
            item = self._data[row]
            conn = get_signal_db()
            conn.execute(
                "DELETE FROM watch_targets WHERE type_id = ? AND region_id = ?",
                (item["type_id"], item["region_id"]),
            )
            conn.commit()
            self.beginRemoveRows(Qt.TopLevel, row, row)
            self._data.pop(row)
            self.endRemoveRows()


class SettingsPage(QWidget):
    """设置页面：管理监控目标和阈值"""

    targets_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # —— 监控目标 ——
        group = QGroupBox("监控目标")
        glayout = QVBoxLayout(group)

        # 工具栏
        toolbar = QHBoxLayout()
        self.type_id_input = QSpinBox()
        self.type_id_input.setRange(1, 999999)
        self.type_id_input.setPrefix("type_id: ")
        self.region_id_input = QSpinBox()
        self.region_id_input.setRange(1, 999999)
        self.region_id_input.setValue(10000002)
        self.region_id_input.setPrefix("区域: ")
        self.label_input = QLineEdit()
        self.label_input.setPlaceholderText("标签（可选）")
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self.add_target)
        delete_btn = QPushButton("删除选中")
        delete_btn.clicked.connect(self.delete_target)

        toolbar.addWidget(self.type_id_input)
        toolbar.addWidget(self.region_id_input)
        toolbar.addWidget(self.label_input)
        toolbar.addWidget(add_btn)
        toolbar.addWidget(delete_btn)
        toolbar.addStretch()
        glayout.addLayout(toolbar)

        # 表格
        self.table_view = QTableView()
        self.model = WatchTargetModel()
        self.table_view.setModel(self.model)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.SingleSelection)
        glayout.addWidget(self.table_view)

        layout.addWidget(group)

        # —— 阈值设置 ——
        threshold_group = QGroupBox("信号阈值")
        tgrid = QGridLayout(threshold_group)

        tgrid.addWidget(QLabel("最低利润率 (%):"), 0, 0)
        self.min_margin = QLineEdit()
        tgrid.addWidget(self.min_margin, 0, 1)

        tgrid.addWidget(QLabel("量比阈值:"), 1, 0)
        self.vol_ratio = QLineEdit()
        tgrid.addWidget(self.vol_ratio, 1, 1)

        tgrid.addWidget(QLabel("价比阈值:"), 2, 0)
        self.price_ratio = QLineEdit()
        tgrid.addWidget(self.price_ratio, 2, 1)

        tgrid.addWidget(QLabel("深度 σ 阈值:"), 3, 0)
        self.depth_sigma = QLineEdit()
        tgrid.addWidget(self.depth_sigma, 3, 1)

        save_btn = QPushButton("保存阈值")
        save_btn.clicked.connect(self.save_settings)
        tgrid.addWidget(save_btn, 4, 0, 1, 2)

        layout.addWidget(threshold_group)
        layout.addStretch()

    def load_settings(self):
        self.min_margin.setText(get_setting("min_profit_margin", "10"))
        self.vol_ratio.setText(get_setting("mom_volume_ratio", "2.0"))
        self.price_ratio.setText(get_setting("mom_price_ratio", "1.05"))
        self.depth_sigma.setText(get_setting("depth_sigma", "2.0"))
        self.model.refresh()

    def save_settings(self):
        set_setting("min_profit_margin", self.min_margin.text().strip())
        set_setting("mom_volume_ratio", self.vol_ratio.text().strip())
        set_setting("mom_price_ratio", self.price_ratio.text().strip())
        set_setting("depth_sigma", self.depth_sigma.text().strip())
        self.targets_changed.emit()

    def add_target(self):
        tid = self.type_id_input.value()
        rid = self.region_id_input.value()
        label = self.label_input.text().strip()
        conn = get_signal_db()
        conn.execute(
            "INSERT OR IGNORE INTO watch_targets (type_id, region_id, label) VALUES (?, ?, ?)",
            (tid, rid, label),
        )
        conn.commit()
        self.model.refresh()
        self.targets_changed.emit()

    def delete_target(self):
        idx = self.table_view.currentIndex()
        if idx.isValid():
            self.model.remove_row(idx.row())
            self.targets_changed.emit()

    def refresh(self):
        self.model.refresh()
