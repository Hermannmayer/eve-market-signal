# eve-market-signal — 量化信号桌面端

## 一、项目定位

现有 **EVE-Online-Industrial-Assistant** 做数据层（拉取 ESI、存储价格、展示物品信息），
**eve-market-signal** 做分析层（信号计算、可视化），两项目独立 repo，通过数据库共享数据。

## 二、目录结构

```
/root/eve-market-signal/
├── run.py                  # 入口：python run.py
├── pyproject.toml          # 同现有项目：target-version=py314, ruff lint
├── AGENTS.md               # Codex 规则文件
│
├── signals/
│   ├── __init__.py
│   ├── db.py               # DB 连接：只读 market.db + 读写 depth.db
│   ├── spread.py           # 信号1：跨区域价差
│   ├── momentum.py         # 信号2：量价趋势
│   └── depth.py            # 信号3：订单簿深度不平衡（依赖 depth.db）
│
├── fetch/
│   ├── __init__.py
│   └── depth_fetcher.py    # ESI 拉取订单簿前 10 档，写入 depth.db
│
├── ui/
│   ├── __init__.py
│   ├── main_window.py      # QMainWindow + 左侧导航树
│   ├── spread_page.py      # 价差机会表格
│   ├── depth_page.py       # 深度不平衡可视化
│   ├── momentum_page.py    # 趋势信号列表
│   └── settings_page.py    # 监控品类/阈值配置
│
├── depth.db                # 自动创建：订单簿深度快照
└── tests/
    ├── test_spread.py
    ├── test_momentum.py
    └── test_depth.py
```

## 三、复用现有项目（不动原项目一行代码）

| 复用内容 | 方式 |
|---------|------|
| `market.db` 读写 | `signals/db.py` 硬编码路径 `/root/EVE-Online-Industrial-Assistant/database/market.db`，`sqlite3.connect()` 只读 |
| `reference.db` 读中文名 | 同上路径，只读 ATTACH 或单独连接 |
| ESI 数据拉取 | **不复用**，新项目只拉订单簿深度（`/markets/{rid}/orders/?type_id={tid}`），与现有价格拉取无冲突 |
| 工具函数 | 复制 `eve_formulas.py` 中的 `resolve_item_name()` 和常量到 `signals/db.py`（< 30 行） |
| PySide6 UI 模式 | 参考 `trade_view.py` 的 QTableView + QTabWidget 模式 |
| 配色素材 | 从 `ui_pyside6/theme.py` 提取基础颜色定义 |

## 四、数据库

### depth.db（新项目的数据库）
```sql
-- 订单簿深度快照
CREATE TABLE IF NOT EXISTS depth_snapshots (
    type_id INTEGER NOT NULL,
    region_id INTEGER NOT NULL,
    fetch_time TEXT NOT NULL,        -- ISO 8601
    mid_price REAL,                  -- (best_bid + best_ask) / 2
    spread_isk REAL,                 -- best_ask - best_bid
    spread_pct REAL,                 -- spread / mid_price * 100
    bid_total_volume REAL,           -- 所有买单挂单总量
    ask_total_volume REAL,           -- 所有卖单挂单总量
    imbalance_ratio REAL,            -- bid_total / ask_total
    top10_bids TEXT,                 -- JSON: [[price, vol], ...]
    top10_asks TEXT,                 -- JSON: [[price, vol], ...]
    PRIMARY KEY (type_id, region_id, fetch_time)
);

-- 监控目标配置（用户选哪些物品跑深度信号）
CREATE TABLE IF NOT EXISTS watch_targets (
    type_id INTEGER NOT NULL,
    region_id INTEGER NOT NULL DEFAULT 10000002,
    label TEXT,                      -- 备注，如"T2弹药"、"矿船"
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (type_id, region_id)
);
```

### 读取 market.db（只读，不写）
使用市场已有 `market_prices` 表做跨区价差，`market_volume_snapshots` 表做趋势信号。

## 五、三个信号详细设计

### 信号1: cross-region spread（跨区域价差）

**输入：** `market_prices` 表（4个区域的最优买/卖价）
**逻辑：**
```
对于每个 type_id:
  buy_region = 有最低 sell_price 的区域
  sell_region = 有最高 buy_price 的区域
  if sell_region != buy_region:
    qty = min(buy_vol, sell_vol)  # 可交易量取小
    毛利润 = (sell_price - buy_price) * qty
    运费 = 从 buy_region 到 sell_region 的公开货运费
    净利润 = 毛利润 - 运费 - 经纪人费 - 税
    利润率 = 净利润 / (buy_price * qty + 运费)
    if 利润率 > threshold (默认 10%):
      发出信号
```
**不跑全量物品**，只跑目标品类列表（在 `watch_targets` 或硬编码列表中指定）。

**实现位置：** `signals/spread.py`

---

### 信号2: volume/price momentum（量价趋势）

**输入：** `market_volume_snapshots` 表
**逻辑：**
```
对于每个 type_id × region_id:
  取最近 30 天每日快照
  
  量比 = 近7日均量 / 近30日均量
  价比 = 当前 sell_price / 30日均价
  
  if 量比 > 2.0 且 价比 > 1.05:
    信号 = "放量上涨"
  elif 量比 > 2.0 且 价比 < 0.95:
    信号 = "放量下跌"
  elif 量比 < 0.5 且 价比 < 0.90:
    信号 = "缩量阴跌（可能见底）"
  elif 价比 > 1.10 且 量比 < 1.5:
    信号 = "无量上涨（可能见顶）"
  else:
    无信号
```
**实现位置：** `signals/momentum.py`

---

### 信号3: order book depth imbalance（深度不平衡）

**输入：** `depth_snapshots` 表
**逻辑：**
```
对于每个 type_id × region_id:
  取最近 N 次深度快照（N = 24 每个小时一次 → 24小时数据）
  
  bid_depth_ratio = bid_total_volume / (bid_total + ask_total)
  normal_range = bid_depth_ratio 的 95% 置信区间（历史均值的 ±2σ）
  
  if bid_depth_ratio > upper_bound:
    信号 = "买单深度异常偏高 → 短期看涨"
  elif bid_depth_ratio < lower_bound:
    信号 = "卖单深度异常偏高 → 短期看跌"
  else:
    无信号
```
**实现位置：** `signals/depth.py`

## 六、Desktop UI 设计

### 窗口结构
```
┌─────────────────────────────────────────┐
│  EVE Market Signal  ─── 标题栏        │
├──────────┬──────────────────────────────┤
│          │  信号概览 (3个tab)           │
│ 导航树   │                              │
│          │  [价差信号]  [深度信号]  [趋势] │
│  ─价差    │                              │
│  ─深度    │ 表格/图表区域                │
│  ─趋势    │                              │
│  ─设置    │  状态栏: 上次更新 3分钟前    │
├──────────┴──────────────────────────────┤
│  状态栏: 信号库 xxx  DB状态             │
└─────────────────────────────────────────┘
```

### 各页具体内容

**spread_page.py（价差）：**
- QTableView + sort proxy model
- 列: 物品名 | 买入区域 | 卖出区域 | 买入价 | 卖出价 | 单件利润 | 利润率% | 可交易量 | 总利润 | 操作
- 顶部过滤器：最小利润率、最低成交量

**depth_page.py（深度）：**
- 每行一个 `watch_target`，显示：
  - 物品名
  - 当前不平衡比率（数字 + 色标：红/绿/黄）
  - 历史均值 + 当前偏离 σ
  - 最新信号等级（无 / 轻度 / 强烈）
- 顶部：折线图显示 imbalance_ratio 最近24小时变化（用 QPainterPath 画简单的趋势线）
- 参考 `gantt_view.py` 的自定义 QWidget 绘图模式

**momentum_page.py（趋势）：**
- 分析项列表，每项：
  - 物品名 | 区域 | 信号标签（放量上涨/无量上涨/放量下跌/缩量阴跌） | 量比 | 价比 | 近7日均量 | 近30日均量
  - 信号标签用 QLabel 设不同背景色（绿涨红跌）

**settings_page.py（设置）：**
- QTableView 编辑 `watch_targets` 表
  - 添加：type_id 输入框 + region 下拉框 + 标签
  - 删除：选中行删除
  - 导入：从 market.db 按品类批量添加（通过 `item.group_id` 过滤）
- 全局阈值：最小利润率、量价比门限、σ 倍数

## 七、执行流程

### 启动时序
```
run.py → main_window.py
           ├─ signals/db.py → 连接 market.db（只读）+ depth.db（读写）
           ├─ 查 depth.db 天气数据
           ├─ 加载各 tab 页
           └─ QTimer 定时刷新（每 60 秒）
```

### 数据更新流程（独立于 UI 刷新）
```
python fetch/depth_fetcher.py        ← cron: 每小时
  → 遍历 depth.db 中 enabled 的 watch_targets
  → ESI /markets/{rid}/orders/?type_id={tid}&order_type=all
  → 聚合前 10 档买卖单
  → 写入 depth_snapshots
```

UI 不直接调 ESI，只读本地库。

## 八、实现顺序（Codex CLI 执行步骤）

```
Phase 1 — 数据层（2 个文件）
  1. signals/db.py         — DB 连接 + 查询封装
  2. fetch/depth_fetcher.py — ESI 拉取深度 + 写入 depth.db

Phase 2 — 信号逻辑（3 个文件）
  3. signals/spread.py     — 跨区价差信号
  4. signals/momentum.py   — 量价趋势信号
  5. signals/depth.py      — 深度不平衡信号

Phase 3 — UI（5 个文件）
  6. ui/settings_page.py   — 监控目标配置
  7. ui/momentum_page.py   — 趋势信号列表
  8. ui/spread_page.py     — 价差机会表格
  9. ui/depth_page.py      — 深度不平衡面板
  10. ui/main_window.py    — 主窗口 + 导航树组装

Phase 4 — 整合（2 个文件）
  11. run.py               — 入口
  12. pyproject.toml       — ruff 配置
```

## 九、注意事项

1. **不碰现有项目代码** — `market.db` 只读，depth.db 独立文件
2. **不碰 ESI 全量拉取** — depth_fetcher 只拉 `watch_targets` 里的 type_id
3. **UI 风格一致** — 沿用 `EVE-Online-Industrial-Assistant` 的配色体系（暗色主题）
4. **信号不执行交易** — 纯可视化展示，用户手动决策
5. **Python 3.14 + PySide6** — 与现有项目一致的版本
6. **测试先行** — 每个信号模块有对应 pytest 测试

## 十、技术依赖

- Python 3.14 stdlib（sqlite3, json, datetime, statistics）
- PySide6（Qt6 桌面端）
- aiohttp + asyncio（depth_fetcher ESI 请求）
- ruff（lint + format）
- pytest（测试）

以上是完整计划。确认后通过 Codex CLI 按 Phase 1→4 顺序执行。
