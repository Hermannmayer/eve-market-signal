"""
测试用 conftest — 提供内存数据库 fixtures
"""

import sqlite3
from collections.abc import Generator

import pytest


def _create_signal_tables(conn: sqlite3.Connection):
    """创建与 signal.db 相同的表结构"""
    conn.executescript("""
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
        CREATE TABLE IF NOT EXISTS user_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)
    conn.commit()


@pytest.fixture
def signal_conn() -> Generator[sqlite3.Connection]:
    """创建内存 signal.db，模拟 signals.db.get_signal_db()"""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _create_signal_tables(conn)
    # 插入默认设置
    defaults = [
        ("min_profit_margin", "10"),
        ("mom_volume_ratio", "2.0"),
        ("mom_price_ratio", "1.05"),
        ("depth_sigma", "2.0"),
    ]
    for k, v in defaults:
        conn.execute(
            "INSERT OR IGNORE INTO user_settings (key, value) VALUES (?, ?)", (k, v)
        )
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def populated_market_prices(signal_conn):
    """填充一些市场价数据用于测试价差信号"""
    # type_id 44992 = PLEX — 窄价差（不足以覆盖税费）
    plex_prices = {
        10000002: (499_000, 500_000, 1000, 500),   # Jita: buy=499k sell=500k
        10000043: (501_000, 502_000, 200, 300),     # Amarr: 更贵
        10000032: (498_000, 499_000, 100, 400),     # Dodixie: 便宜
        10000030: (497_000, 498_000, 50, 100),      # Rens: 更便宜
    }
    for rid, (buy, sell, bvol, svol) in plex_prices.items():
        signal_conn.execute(
            "INSERT INTO market_prices (type_id, region_id, buy_price, sell_price, buy_volume, sell_volume) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (44992, rid, buy, sell, bvol, svol),
        )

    # type_id 2 — 宽价差（Rens 卖 100, Jita 买 5000 => 4900/件利润）
    wide_prices = {
        10000002: (5000, 5100, 1000, 500),    # Jita: buy=5000 sell=5100
        10000030: (100, 200, 500, 100),        # Rens: buy=100 sell=200
    }
    for rid, (buy, sell, bvol, svol) in wide_prices.items():
        signal_conn.execute(
            "INSERT INTO market_prices (type_id, region_id, buy_price, sell_price, buy_volume, sell_volume) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (2, rid, buy, sell, bvol, svol),
        )
    signal_conn.commit()


@pytest.fixture
def populated_volume(signal_conn):
    """填充历史量价数据用于测试趋势信号"""
    tid = 44992
    rid = 10000002
    # 30 天数据：近 7 天放量
    for i in range(30):
        day = f"2025-06-{i+1:02d}"
        vol = 5000 if i < 23 else 15000  # 近 7 天量变大
        price = 500 if i < 23 else 520   # 价格上涨
        signal_conn.execute(
            "INSERT INTO volume_snapshots (type_id, region_id, date, buy_price, sell_price, buy_volume, sell_volume) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (tid, rid, day, price, price, vol, vol),
        )
    signal_conn.commit()


@pytest.fixture
def populated_target(signal_conn):
    """插入监控目标"""
    signal_conn.execute(
        "INSERT OR IGNORE INTO watch_targets (type_id, region_id, label, enabled) VALUES (?, ?, ?, ?)",
        (44992, 10000002, "PLEX", 1),
    )
    signal_conn.commit()


@pytest.fixture
def populated_depth(signal_conn):
    """填充深度快照用于测试深度信号"""
    tid = 44992
    rid = 10000002
    # 24 条快照，imbalance 围绕 1.0 波动
    ratios = [1.0, 0.95, 1.05, 0.98, 1.02, 1.01, 0.99, 1.03,
              0.97, 1.04, 0.96, 1.06, 0.94, 1.07, 0.93, 1.08,
              0.92, 1.09, 0.91, 1.10, 0.90, 1.11, 0.89, 3.5]  # 最后一条异常高
    for i, r in enumerate(ratios):
        signal_conn.execute(
            "INSERT INTO depth_snapshots (type_id, region_id, fetch_time, imbalance_ratio, "
            "mid_price, spread_isk, spread_pct, bid_total_volume, ask_total_volume, top10_bids, top10_asks) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (tid, rid, f"2025-07-{i+1:02d}T00:00:00",
             r, 500, 1.0, 0.2, 1000 * r, 1000, "[]", "[]"),
        )
    signal_conn.commit()
