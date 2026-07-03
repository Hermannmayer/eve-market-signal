"""
主窗口 — 左侧导航树 + 右侧信号页面
"""

import logging

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QWidget,
)

from ui.depth_page import DepthPage
from ui.momentum_page import MomentumPage
from ui.settings_page import SettingsPage
from ui.spread_page import SpreadPage
from ui.technical_page import TechnicalPage

logger = logging.getLogger(__name__)

PAGES = [
    ("跨区域价差", "spread"),
    ("深度不平衡", "depth"),
    ("技术指标", "technical"),
    ("量价趋势", "momentum"),
    ("设置", "settings"),
]


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("EVE Market Signal")
        self.resize(1100, 700)

        self.setup_ui()
        self.setup_timer()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # 分割器
        self.splitter = QSplitter()
        layout.addWidget(self.splitter)

        # === 左侧导航 ===
        self.nav = QListWidget()
        self.nav.setMinimumWidth(120)
        self.nav.setMaximumWidth(180)
        for name, _ in PAGES:
            self.nav.addItem(name)
        self.nav.currentRowChanged.connect(self._on_page_change)
        self.splitter.addWidget(self.nav)

        # === 右侧页面 ===
        self.stack = QStackedWidget()

        self.spread_page = SpreadPage()
        self.depth_page = DepthPage()
        self.technical_page = TechnicalPage()
        self.momentum_page = MomentumPage()
        self.settings_page = SettingsPage()
        self.settings_page.targets_changed.connect(self._on_targets_changed)

        self.stack.addWidget(self.spread_page)       # 0
        self.stack.addWidget(self.depth_page)         # 1
        self.stack.addWidget(self.technical_page)     # 2
        self.stack.addWidget(self.momentum_page)      # 3
        self.stack.addWidget(self.settings_page)      # 4
        self.splitter.addWidget(self.stack)

        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)

        # === 状态栏 ===
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status_label = QLabel("就绪")
        self.status.addPermanentWidget(self.status_label)

        # 默认选中第一页
        self.nav.setCurrentRow(0)

    def setup_timer(self):
        """每 60 秒自动刷新当前页"""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._auto_refresh)
        self.timer.start(60000)

    def _on_page_change(self, idx: int):
        if 0 <= idx < self.stack.count():
            self.stack.setCurrentIndex(idx)
            self._refresh_current()

    def _refresh_current(self):
        idx = self.stack.currentIndex()
        try:
            if idx == 0:
                self.spread_page.refresh()
                self.status_label.setText("价差信号已刷新")
            elif idx == 1:
                self.depth_page.refresh()
                self.status_label.setText("深度信号已刷新")
            elif idx == 2:
                self.technical_page.refresh()
                self.status_label.setText("技术指标已刷新")
            elif idx == 3:
                self.momentum_page.refresh()
                self.status_label.setText("趋势信号已刷新")
            elif idx == 4:
                self.settings_page.refresh()
                self.status_label.setText("设置已加载")
        except Exception as e:
            logger.exception("刷新失败")
            self.status_label.setText(f"刷新失败: {e}")

    def _auto_refresh(self):
        """定时自动刷新"""
        if self.isVisible():
            self.status_label.setText("自动刷新…")
            self._refresh_current()

    def _on_targets_changed(self):
        """监控目标变更后更新状态"""
        self.status_label.setText("监控目标已更新")
