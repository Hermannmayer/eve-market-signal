# eve-market-signal — 量化信号桌面端

## 项目定位

独立于 EVE-Online-Industrial-Assistant 的量化信号分析桌面端。通过自建的数据管道（SDE + ESI）获取所需数据，不依赖任何外部项目。

## 数据源

| 数据 | 来源 | 数据库 |
|------|------|--------|
| 物品名称+分组 | SDE (Static Data Export) | `reference.db` |
| 市场价格+订单簿 | ESI `/markets/{rid}/orders/` | `signal.db` |
| 历史量价 | ESI `/markets/{rid}/history/` | `signal.db` |
| 订单簿深度 | ESI `/markets/{rid}/orders/?type_id=` | `signal.db` |
| 用户配置 | Settings UI | `settings.db` |

## 数据库结构

### reference.db (SDE 构建一次)

```sql
-- 物品名称
CREATE TABLE item (
    type_id INTEGER PRIMARY KEY,
    en_name TEXT, zh_name TEXT,
    group_id INTEGER,
    en_group_name TEXT, zh_group_name TEXT,
    market_group_id INTEGER,
    en_market_group_name TEXT, zh_market_group_name TEXT,
    volume REAL, iconID INTEGER
);

-- 市场分类树
CREATE TABLE market_tree (
    market_group_id INTEGER PRIMARY KEY,
    parent_group_id INTEGER,
    en_name TEXT, zh_name TEXT, icon_id INTEGER
);
```

### signal.db (动态数据)

```sql
-- 市场价（每次刷全新写）
CREATE TABLE market_prices (
    type_id INTEGER NOT NULL,
    region_id INTEGER NOT NULL,
    buy_price REAL,
    sell_price REAL,
    buy_volume BIGINT DEFAULT 0,
    sell_volume BIGINT DEFAULT 0,
    fetch_time TIMESTAMP NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (type_id, region_id)
);

-- 成交量快照（每日追加）
CREATE TABLE volume_snapshots (
    type_id INTEGER NOT NULL,
    region_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    buy_price REAL DEFAULT 0,
    sell_price REAL DEFAULT 0,
    buy_volume BIGINT DEFAULT 0,
    sell_volume BIGINT DEFAULT 0,
    PRIMARY KEY (type_id, region_id, date)
);

-- 深度快照（每次拉取追加）
CREATE TABLE depth_snapshots (
    type_id INTEGER NOT NULL,
    region_id INTEGER NOT NULL,
    fetch_time TEXT NOT NULL,
    mid_price REAL,
    spread_isk REAL, spread_pct REAL,
    bid_total_volume REAL, ask_total_volume REAL,
    imbalance_ratio REAL,
    top10_bids TEXT, top10_asks TEXT,
    PRIMARY KEY (type_id, region_id, fetch_time)
);

-- 监控目标
CREATE TABLE watch_targets (
    type_id INTEGER NOT NULL,
    region_id INTEGER NOT NULL DEFAULT 10000002,
    label TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (type_id, region_id)
);

-- ESI 名称缓存
CREATE TABLE name_cache (
    type_id INTEGER PRIMARY KEY,
    en_name TEXT, zh_name TEXT,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

## 三个信号详细设计

### 信号1: 跨区域价差

**输入:** `market_prices` 表（4个区域的买卖价）
**逻辑:**
```
对于每个 type_id:
  buy_region = 有最低 sell_price 的区域
  sell_region = 有最高 buy_price 的区域
  if sell_region != buy_region:
    qty = min(buy_vol, sell_vol)
    净利润 = (sell_price - buy_price)*qty - 运费 - 经纪人费 - 税
    利润率 = 净利润 / (buy_price*qty + 运费) * 100
    if 利润率 > 阈值: 发出信号
```

### 信号2: 量价趋势

**输入:** `volume_snapshots` 表
**逻辑:**
```
量比 = 近7日均量 / 近30日均量
价比 = 当前价格 / 30日均价

放量上涨: 量比 > 2.0 AND 价比 > 1.05
放量下跌: 量比 > 2.0 AND 价比 < 0.95
缩量阴跌: 量比 < 0.5 AND 价比 < 0.90
无量上涨: 价比 > 1.10 AND 量比 < 1.5
```

### 信号3: 深度不平衡

**输入:** `depth_snapshots` 表
**逻辑:**
```
bid_depth_ratio = bid_total / (bid_total + ask_total)
sigma = (当前比率 - 历史均值) / 历史标准差

if sigma >= 2σ: "买单深度异常偏高 → 短期看涨"
if sigma <= -2σ: "卖单深度异常偏高 → 短期看跌"
```

## 实现状态

- [x] Phase 0: 修复已有文件 (eve_reuse/)
- [x] Phase 1: 数据层 (ESI 客户端、数据库、3个 fetcher、reference builder)
- [x] Phase 2: 信号计算 (spread, momentum, depth)
- [x] Phase 3: UI (5个页面) + 入口 + 配置
- [x] Phase 4: 测试 (3个信号模块) + 文档

## 技术依赖

- Python 3.14 stdlib (sqlite3, json, datetime, statistics)
- PySide6 (Qt6 桌面端)
- aiohttp + asyncio (ESI 请求)
- PyYAML (SDE 解析)
- pytest (测试)
- ruff (lint + format)
