"""
EVE Market Signal — 入口

用法:
    python run.py              # 启动桌面端
    python run.py --init       # 仅初始化数据库
    python run.py --update     # 更新市场数据后启动
"""

import logging
import sys

from PySide6.QtWidgets import QApplication

from eve_reuse.paths import ensure_dirs_exist
from signals.db import init_databases
from ui.main_window import MainWindow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("run")


def main():
    # 确保目录存在
    ensure_dirs_exist()

    # 确保数据库和表存在
    init_databases()

    # CLI 参数
    if "--init" in sys.argv:
        logger.info("数据库已初始化")
        return

    if "--update" in sys.argv:
        logger.info("更新市场数据…")
        from fetch.market_fetcher import run_price_update
        run_price_update()
        logger.info("市场数据已更新")

    # 启动桌面 UI
    app = QApplication(sys.argv)
    app.setApplicationName("EVE Market Signal")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
