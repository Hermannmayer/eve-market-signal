"""
集中式路径管理 —— 独立于 EVE-Online-Industrial-Assistant 的项目

eve-market-signal/
├── run.py
├── database/
│   ├── reference.db       ← 物品名称（SDE 构建）
│   ├── signal.db          ← 市场价 / 深度快照 / 监控目标
│   └── settings.db        ← 用户配置
├── data/
│   ├── typeIDs.yaml       ← SDE 缓存
│   └── groupIDs.yaml      ← SDE 缓存
├── fetch/
├── signals/
├── ui/
└── tests/
"""

import os
import sys


def is_frozen() -> bool:
    """判断是否运行在 PyInstaller 打包后的环境中"""
    return getattr(sys, "frozen", False)


def app_root() -> str:
    """返回应用根目录"""
    if is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def database_dir() -> str:
    """数据库目录"""
    return os.path.join(app_root(), "database")


def reference_db_path() -> str:
    """物品名称参考数据库"""
    return os.path.join(database_dir(), "reference.db")


def signal_db_path() -> str:
    """市场价格 / 深度 / 监控目标数据库"""
    return os.path.join(database_dir(), "signal.db")


def settings_db_path() -> str:
    """用户配置数据库"""
    return os.path.join(database_dir(), "settings.db")


def data_dir() -> str:
    """SDE 缓存等数据目录"""
    return os.path.join(app_root(), "data")


def ensure_dirs_exist():
    """确保所有必要目录存在"""
    os.makedirs(database_dir(), exist_ok=True)
    os.makedirs(data_dir(), exist_ok=True)
