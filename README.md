# EVE Market Signal

EVE Online 市场量化信号桌面端。独立于 [EVE-Online-Industrial-Assistant](https://github.com/Hermannmayer/EVE-Online-Industrial-Assistant) 的信号分析层项目，通过读取其数据库生成交易信号。

## 功能

- **跨区域价差** — 四大贸易中心之间最优买入/卖出区域的套利机会检测
- **量价趋势** — 基于历史快照的放量突破/缩量阴跌/趋势背离信号
- **深度不平衡** — 订单簿前 10 档买卖挂单偏离统计基线时发出反转信号

## 数据源

| 数据 | 来源 | 访问方式 |
|------|------|---------|
| 市场成交价 | `EVE-Online-Industrial-Assistant/database/market.db` | 只读 |
| 物品信息 | `EVE-Online-Industrial-Assistant/database/reference.db` | 只读 |
| 订单簿深度 | ESI `/markets/{region}/orders/` | 新项目自取存 `depth.db` |

## 快速开始

```bash
# 进入项目
cd eve-market-signal

# 启动桌面端
python run.py

# 单独刷新深度数据（cron 每小时执行）
python -m fetch.depth_fetcher
```

## 项目结构

```
eve-market-signal/
├── run.py                  入口
├── signals/                信号计算（spread / momentum / depth）
├── fetch/                  ESI 数据拉取
├── ui/                     PySide6 桌面界面
├── eve_reuse/              从原项目复用的工具模块
└── tests/                  单元测试
```

## 许可

Apache 2.0
