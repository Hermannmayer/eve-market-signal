"""
数据库层 — 管理 signal.db / reference.db / settings.db 的初始化和查询
"""

import sqlite3
import threading
from collections.abc import Generator
from contextlib import contextmanager

from eve_reuse.paths import ensure_dirs_exist, reference_db_path, settings_db_path, signal_db_path

_LOCAL = threading.local()


# ── 数据库初始化 ──────────────────────────────────────────


def get_signal_db() -> sqlite3.Connection:
    """获取当前线程的 signal.db 连接"""
    if not hasattr(_LOCAL, "signal_conn") or _LOCAL.signal_conn is None:
        _LOCAL.signal_conn = sqlite3.connect(signal_db_path())
        _LOCAL.signal_conn.row_factory = sqlite3.Row
        _LOCAL.signal_conn.execute("PRAGMA journal_mode=WAL")
    return _LOCAL.signal_conn


def get_ref_db() -> sqlite3.Connection:
    """获取当前线程的 reference.db 连接"""
    if not hasattr(_LOCAL, "ref_conn") or _LOCAL.ref_conn is None:
        _LOCAL.ref_conn = sqlite3.connect(reference_db_path())
        _LOCAL.ref_conn.row_factory = sqlite3.Row
    return _LOCAL.ref_conn


def get_settings_db() -> sqlite3.Connection:
    """获取当前线程的 settings.db 连接"""
    if not hasattr(_LOCAL, "settings_conn") or _LOCAL.settings_conn is None:
        _LOCAL.settings_conn = sqlite3.connect(settings_db_path())
        _LOCAL.settings_conn.row_factory = sqlite3.Row
    return _LOCAL.settings_conn


@contextmanager
def signal_db() -> Generator[sqlite3.Connection]:
    """signal.db 上下文管理器"""
    conn = get_signal_db()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


@contextmanager
def ref_db() -> Generator[sqlite3.Connection]:
    """reference.db 上下文管理器"""
    conn = get_ref_db()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


# ── 建表 ──────────────────────────────────────────


SIGNAL_DDL = """
CREATE TABLE IF NOT EXISTS market_prices (
    type_id INTEGER NOT NULL,
    region_id INTEGER NOT NULL,
    buy_price REAL,
    sell_price REAL,
    buy_volume BIGINT DEFAULT 0,
    sell_volume BIGINT DEFAULT 0,
    fetch_time TIMESTAMP NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (type_id, region_id)
);

CREATE TABLE IF NOT EXISTS volume_snapshots (
    type_id INTEGER NOT NULL,
    region_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    buy_price REAL DEFAULT 0,
    sell_price REAL DEFAULT 0,
    buy_volume BIGINT DEFAULT 0,
    sell_volume BIGINT DEFAULT 0,
    order_count INTEGER DEFAULT 0,
    PRIMARY KEY (type_id, region_id, date)
);

CREATE TABLE IF NOT EXISTS depth_snapshots (
    type_id INTEGER NOT NULL,
    region_id INTEGER NOT NULL,
    fetch_time TEXT NOT NULL,
    mid_price REAL,
    spread_isk REAL,
    spread_pct REAL,
    bid_total_volume REAL,
    ask_total_volume REAL,
    imbalance_ratio REAL,
    top10_bids TEXT,
    top10_asks TEXT,
    PRIMARY KEY (type_id, region_id, fetch_time)
);

CREATE TABLE IF NOT EXISTS watch_targets (
    type_id INTEGER NOT NULL,
    region_id INTEGER NOT NULL DEFAULT 10000002,
    label TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (type_id, region_id)
);

CREATE TABLE IF NOT EXISTS name_cache (
    type_id INTEGER PRIMARY KEY,
    en_name TEXT,
    zh_name TEXT,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

REFERENCE_DDL = """
CREATE TABLE IF NOT EXISTS item (
    type_id INTEGER PRIMARY KEY,
    en_name TEXT,
    zh_name TEXT,
    group_id INTEGER,
    en_group_name TEXT,
    zh_group_name TEXT,
    market_group_id INTEGER,
    en_market_group_name TEXT,
    zh_market_group_name TEXT,
    volume REAL,
    iconID INTEGER
);

CREATE TABLE IF NOT EXISTS market_tree (
    market_group_id INTEGER PRIMARY KEY,
    parent_group_id INTEGER,
    en_name TEXT,
    zh_name TEXT,
    icon_id INTEGER
);
"""

SETTINGS_DDL = """
CREATE TABLE IF NOT EXISTS user_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def init_databases():
    """确保所有数据库和表存在"""
    ensure_dirs_exist()
    with signal_db() as conn:
        conn.executescript(SIGNAL_DDL)
    with ref_db() as conn:
        conn.executescript(REFERENCE_DDL)
    with get_settings_db() as conn:
        conn.executescript(SETTINGS_DDL)
    # 插入默认设置
    defaults = {
        "min_profit_margin": "10",
        "mom_volume_ratio": "2.0",
        "mom_price_ratio": "1.05",
        "depth_sigma": "2.0",
    }
    with get_settings_db() as conn:
        for k, v in defaults.items():
            conn.execute(
                "INSERT OR IGNORE INTO user_settings (key, value) VALUES (?, ?)",
                (k, v),
            )
        conn.commit()


# ── 配置查询 ──────────────────────────────────────────


def get_setting(key: str, default: str = "") -> str:
    """读取用户设置"""
    conn = get_settings_db()
    row = conn.execute(
        "SELECT value FROM user_settings WHERE key = ?", (key,)
    ).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str):
    """写入用户设置"""
    conn = get_settings_db()
    conn.execute(
        "INSERT OR REPLACE INTO user_settings (key, value) VALUES (?, ?)",
        (key, value),
    )
    conn.commit()


# ── 物品名查询 ──────────────────────────────────────────


def resolve_item_name(type_id: int) -> str:
    """查询物品中文名，fallback 链：reference.db → name_cache → str(id)"""
    from eve_reuse.eve_formulas import _MINERAL_NAMES

    if type_id in _MINERAL_NAMES:
        return _MINERAL_NAMES[type_id]

    # reference.db
    try:
        ref = get_ref_db()
        row = ref.execute(
            "SELECT zh_name, en_name FROM item WHERE type_id = ?", (type_id,)
        ).fetchone()
        if row:
            return row["zh_name"] or row["en_name"] or str(type_id)
    except Exception:
        pass

    # name_cache fallback
    try:
        sig = get_signal_db()
        row = sig.execute(
            "SELECT en_name FROM name_cache WHERE type_id = ?", (type_id,)
        ).fetchone()
        if row and row["en_name"]:
            return row["en_name"]
    except Exception:
        pass

    return str(type_id)
