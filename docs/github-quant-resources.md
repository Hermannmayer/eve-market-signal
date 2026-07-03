# GitHub 量化交易学习资源汇总

> 收集时间：2026-07-03
> 数据来源：GitHub API

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

---

## 三、量化交易框架（实战级）

| 仓库 | ⭐ Stars | 说明 |
|------|---------|------|
| [vnpy/vnpy](https://github.com/vnpy/vnpy) | 42,600+ | 国内最火的开源量化交易平台，基于 Python，支持 A股/期货/加密货币 |
| [freqtrade/freqtrade](https://github.com/freqtrade/freqtrade) | 52,000+ | 免费开源的加密货币量化交易机器人 |
| [mementum/backtrader](https://github.com/mementum/backtrader) | 22,200+ | 最流行的 Python 回测框架，适合学习和策略回测 |
| [QuantConnect/Lean](https://github.com/QuantConnect/Lean) | 20,300+ | QuantConnect 的算法交易引擎（支持 C#/Python） |
| [quantopian/zipline](https://github.com/quantopian/zipline) | 19,900+ | Quantopian 出品的 Pythonic 算法交易库（经典，但已停止维护） |
| [StockSharp/StockSharp](https://github.com/StockSharp/StockSharp) | 10,200+ | 算法交易和量化交易开源平台（股票/外汇/加密货币/期权） |
| [fmzquant/strategies](https://github.com/fmzquant/strategies) | 5,200+ | FMZ量化平台的策略集合，支持 JavaScript/Python/C++/PineScript |
| [Lumiwealth/lumibot](https://github.com/Lumiwealth/lumibot) | 1,700+ | 可回测的 AI 交易代理，支持股票/期权/加密货币/外汇 |

---

## 四、AI + 机器学习量化交易

| 仓库 | ⭐ Stars | 说明 |
|------|---------|------|
| [google/tf-quant-finance](https://github.com/google/tf-quant-finance) | 5,400+ | Google 出品的高性能 TensorFlow 量化金融库 |
| [QuantConnect/HandsOnAITradingBook](https://github.com/QuantConnect/HandsOnAITradingBook) | 346 | 《Hands On AI Trading with Python, QuantConnect, and AWS》配套代码 |

---

## 学习路线建议

如果你是从零开始，建议按这个顺序学习：

1. **先看资源索引** → 浏览 `awesome-quant` 或 `thuquant/awesome-quant`，了解整个知识地图
2. **学习 Python 基础** → 重点掌握 `pandas`、`numpy`、`matplotlib`
3. **从回测框架入手** → 用 `backtrader` 跑第一个策略（如双均线交叉，这是量化领域的 "Hello World"）
4. **阅读策略代码** → 看 `je-suis-tm/quant-trading` 中的实战策略
5. **尝试全功能平台** → `vnpy`（国内首选）或 `freqtrade`（加密货币方向）
6. **深入学习金融模型** → 看 `cantaro86/Financial-Models-Numerical-Methods`
7. **进阶：AI量化** → 研究 `georgezouq/awesome-ai-in-finance`
