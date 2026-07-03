# GitHub 量化交易学习资源汇总

> 收集时间：2026-07-03
> 数据来源：GitHub API + AnySearch

---

## 一、资源索引大全（最佳入门起点）

| 仓库 | ⭐ Stars | 说明 |
|------|---------|------|
| [wilsonfreitas/awesome-quant](https://github.com/wilsonfreitas/awesome-quant) | 27,300+ | 量化金融资源的精选列表，涵盖 Python/R/Julia 库、书籍、博客等，最全索引 |
| [paperswithbacktest/awesome-systematic-trading](https://github.com/paperswithbacktest/awesome-systematic-trading) | 8,400+ | 系统性交易资源集合：策略、书籍、博客、教程一应俱全 |
| [thuquant/awesome-quant](https://github.com/thuquant/awesome-quant) | 5,400+ | 清华Quant整理的中文量化资源索引，对国内用户很友好 |
| [EliteQuant/EliteQuant](https://github.com/EliteQuant/EliteQuant) | 3,900+ | 量化建模、交易、投资组合管理的线上资源列表 |
| [georgezouq/awesome-ai-in-finance](https://github.com/georgezouq/awesome-ai-in-finance) | 6,200+ | AI + 深度学习在金融领域应用的精选资源列表 |

---

## 二、Python 学习教程类

| 仓库 | ⭐ Stars | 说明 |
|------|---------|------|
| [goldmansachs/gs-quant](https://github.com/goldmansachs/gs-quant) | 11,000+ | 高盛官方出品的 Python 量化金融工具包，业界标杆 |
| [cantaro86/Financial-Models-Numerical-Methods](https://github.com/cantaro86/Financial-Models-Numerical-Methods) | 6,900+ | 量化金融数值方法的交互式 Jupyter Notebook 合集，适合深入学习金融模型 |
| [shashankvemuri/Finance](https://github.com/shashankvemuri/Finance) | 4,000+ | 150+ 个量化金融 Python 程序，涵盖数据获取、分析和交易 |
| [LongOnly/Quantitative-Notebooks](https://github.com/LongOnly/Quantitative-Notebooks) | 1,300+ | 量化金融、算法交易的教育型 Notebooks |
| [je-suis-tm/quant-trading](https://github.com/je-suis-tm/quant-trading) | 10,200+ | Python 量化交易策略实战合集（VIX、MACD、RSI、配对交易等大量策略代码） |
| [datawhalechina/whale-quant](https://github.com/datawhalechina/whale-quant) | 2,300+ | 🏆 Datawhale 量化开源课程，完整的中文量化学习教程，含 Notobook |
| [waylandz/ai-quant-book](https://github.com/dnalyaw/ai-quant-book)（待补全） | - | 《AI量化交易从0到1：多智能体量化交易系统实战》配套代码 |

---

## 三、量化交易框架（实战级）

| 仓库 | ⭐ Stars | 说明 |
|------|---------|------|
| [vnpy/vnpy](https://github.com/vnpy/vnpy) | 42,600+ | 🏆 **国内最火的开源量化交易平台**，基于 Python，事件驱动，支持 A股/期货/加密货币 |
| [freqtrade/freqtrade](https://github.com/freqtrade/freqtrade) | 52,000+ | 🏆 免费开源的加密货币量化交易机器人 |
| [mementum/backtrader](https://github.com/mementum/backtrader) | 22,200+ | 最流行的 Python 回测框架，适合学习和策略回测 |
| [QuantConnect/Lean](https://github.com/QuantConnect/Lean) | 20,300+ | QuantConnect 的算法交易引擎（支持 C#/Python），自带数据和实盘接口 |
| [quantopian/zipline](https://github.com/quantopian/zipline) | 19,900+ | Quantopian 出品的 Pythonic 算法交易库（经典，但已停止维护） |
| [StockSharp/StockSharp](https://github.com/StockSharp/StockSharp) | 10,200+ | 算法交易和量化交易开源平台（股票/外汇/加密货币/期权） |
| [fmzquant/strategies](https://github.com/fmzquant/strategies) | 5,200+ | FMZ量化平台的策略集合，支持 JavaScript/Python/C++/PineScript/麦语言 |
| [Lumiwealth/lumibot](https://github.com/Lumiwealth/lumibot) | 1,700+ | 可回测的 AI 交易代理，支持股票/期权/加密货币/外汇 |
| [nautilustrader/nautilus_trader](https://github.com/nautechsystems/nautilus_trader) | 5,000+（估） | Rust 核心 + Python 的高性能算法交易平台 |

### 框架对比（2026 年视角）

| 框架 | 适合人群 | 核心优势 | 局限 |
|------|---------|---------|------|
| **backtrader** | 个人研究者、初学者 | 简单易用，策略代码量少，社区庞大 | 不支持多市场实盘，性能一般 |
| **vnpy** | 国内专业团队、多市场交易 | 事件驱动架构，全栈平台（GUI+回测+实盘），国内券商直连 | 较重，学习曲线陡，架构过度工程化 |
| **QuantConnect/Lean** | 全球用户、云端量化 | 自带数据 + 云端 IDE + 回测 + 实盘一条龙 | 云端受限于平台，自部署较复杂 |
| **NautilusTrader** | 高频/低延迟需求 | Rust 核心，性能极高，Tick 级回测 | 社区相对较小 |

---

## 四、AI + 机器学习量化交易

| 仓库 | ⭐ Stars | 说明 |
|------|---------|------|
| [google/tf-quant-finance](https://github.com/google/tf-quant-finance) | 5,400+ | Google 出品的高性能 TensorFlow 量化金融库 |
| [QuantConnect/HandsOnAITradingBook](https://github.com/QuantConnect/HandsOnAITradingBook) | 346 | 《Hands On AI Trading with Python, QuantConnect, and AWS》配套代码 |
| [0xemmkty/QuantMuse](https://github.com/0xemmkty/QuantMuse) | 2,600+ | 全栈 AI 量化交易系统，支持 LLM 分析、因子模型、风控管理 |

---

## 五、推荐学习路径

### 免费课程 / 社区教程

- **[B站] Python金融分析与量化交易实战教程**（70集）
  - 从金融时间序列分析 → 双均线策略 → 因子选股 → 机器学习，最完整的免费视频课
  - 链接：https://www.bilibili.com/video/BV1gqXzYiEf4/

- **[腾讯云] Python量化学习路线（图文）**
  - 5 阶段学习路线：基础语法 → 量化概念 → 量化技术 → 建立系统 → 持续改进
  - 链接：https://cloud.tencent.com/developer/article/2489879

### 推荐书籍

| 书名 | 作者 | 适合阶段 |
|------|------|---------|
| 《Quantitative Trading》2nd Ed (2026) | Ernest P. Chan | 入门 - 系统化构建量化交易业务 |
| 《AI量化交易从0到1》 (2025) | Wayland Zhang | 进阶 - 多智能体量化系统 |
| 《Python for Finance》 | Yves Hilpisch | 入门 - Python 金融编程 |
| 《Advances in Financial Machine Learning》 | Marcos López de Prado | 进阶 - 机器学习在量化中的应用 |

---

## 六、学习路线建议（整合版）

### 如果你是从零开始

1. **先看资源索引** → 浏览 `awesome-quant` 或 `datawhalechina/whale-quant`，了解整个知识地图
2. **学习 Python 基础** → 重点掌握 numpy、pandas、matplotlib
3. **从回测框架入手** → 用 backtrader 跑第一个策略（双均线交叉，量化 "Hello World"）
4. **阅读策略代码** → 看 `je-suis-tm/quant-trading` 中的实战策略
5. **尝试全功能平台** → vnpy（国内首选）或 freqtrade（加密货币方向）
6. **深入学习金融模型** → 看 `cantaro86/Financial-Models-Numerical-Methods`
7. **进阶：AI量化** → 研究 `georgezouq/awesome-ai-in-finance` 或 `0xemmkty/QuantMuse`

### 基于你这个 EVE 项目的学习路径

1. **Phase 1**：完成现有三个信号（价差/动量/深度），跑通 UI 看到信号输出
2. **Phase 2**：加 `backtest/` 回测模块，验证你的信号是否赚钱
3. **Phase 3**：在 EVE 数据上实现配对交易（找 Tritanium + Pyerite 等高相关物品）
4. **Phase 4**：把 evesml 的 ESI 客户端替换为 ccxt，桥接到真实交易所（Binance 等）
5. **Phase 5**：引入 AI 信号（LLM 分析市场情绪、LSTM 价格预测等）
