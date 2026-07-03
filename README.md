# EVE Market Signal

EVE Online 市场量化信号桌面端。

## 功能

- **跨区域价差** — 四大贸易中心之间最优买入/卖出区域的套利机会检测
- **量价趋势** — 基于历史快照的放量突破/缩量阴跌/趋势背离信号
- **深度不平衡** — 订单簿前 10 档买卖挂单偏离统计基线时发出反转信号

## 数据流

```
  ┌──────────────┐    ┌──────────────┐
  │  SDE (CCP)   │    │  ESI (CCP)   │
  │  物品名称库   │    │  市场数据     │
  └──────┬───────┘    └──────┬───────┘
         │ 一次下载永久缓存    │ 每次用户触发
         ▼                   ▼
  ┌──────────────┐    ┌──────────────┐
  │ reference.db │    │  signal.db   │
  │ 物品名+分组   │    │ 价格+深度+历史 │
  └──────────────┘    └──────┬───────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        spread.py      momentum.py     depth.py
        跨区域价差        量价趋势        深度不平衡
```

| 数据 | 来源 | 存储 |
|------|------|------|
| 物品名称 | SDE (Static Data Export) | `database/reference.db` |
| 市场价格 | ESI `/markets/prices/` + 订单簿 | `database/signal.db` |
| 历史量价 | ESI `/markets/{rid}/history/` | `database/signal.db` |
| 订单簿深度 | ESI `/markets/{rid}/orders/` | `database/signal.db` |
| 用户配置 | Settings UI | `database/settings.db` |

## 快速开始

```bash
# 1. 安装依赖
pip install -U PySide6 aiohttp pyyaml pytest

# 2. 构建参考数据（首次运行，下载 SDE 约 112MB）
python -c "import asyncio; from fetch.reference_builder import build_reference; asyncio.run(build_reference())"

# 3. 拉取市场数据
python -c "from fetch.market_fetcher import run_price_update; run_price_update()"

# 4. 启动桌面端
python run.py

# 单独刷新深度数据（可 cron 每小时执行）
python -m fetch.depth_fetcher
```

## 项目结构

```
eve-market-signal/
├── run.py                    入口
├── pyproject.toml            ruff/mypy 配置
├── database/                 数据库（自动创建）
├── data/                    SDE 缓存（自动创建）
├── eve_reuse/                复用工具（常量、公式、路径）
├── fetch/                    ESI 数据拉取
│   ├── esi_client.py         ESI API 客户端（限流、重试）
│   ├── market_fetcher.py     市场价格 + 订单簿
│   ├── history_fetcher.py    历史量价
│   ├── depth_fetcher.py      订单簿深度
│   └── reference_builder.py  从 SDE 构建物品名库
├── signals/                  信号计算
│   ├── db.py                 数据库管理
│   ├── spread.py             跨区域价差
│   ├── momentum.py           量价趋势
│   └── depth.py              深度不平衡
├── ui/                       PySide6 桌面界面
│   ├── main_window.py        主窗口
│   ├── spread_page.py        价差表格
│   ├── momentum_page.py      趋势列表
│   ├── depth_page.py         深度面板
│   └── settings_page.py      配置
└── tests/                    单元测试
    ├── conftest.py
    ├── test_spread.py
    ├── test_momentum.py
    └── test_depth.py
```

## 依赖

- Python 3.14+
- PySide6 ~= 6.8
- aiohttp ~= 3.11
- PyYAML ~= 6.0
- pytest ~= 8.0（开发）

## 许可

Apache 2.0
