"""
技术指标信号测试 — RSI / MACD / 布林带
"""

from unittest.mock import patch

import pandas as pd

from signals.technical import (
    _compute_bb,
    _compute_macd,
    _compute_rsi,
    compute_technical,
)


class TestIndicatorComputation:
    """指标计算逻辑测试"""

    def test_rsi_uptrend_is_high(self):
        """持续上涨 → RSI 应接近 100"""
        prices = pd.Series([float(i) for i in range(1, 31)])  # 1,2,3,...,30
        rsi = _compute_rsi(prices)
        assert rsi is not None
        last = float(rsi.iloc[-1])
        assert last > 70, f"上涨趋势 RSI 应 > 70, 实际 {last}"

    def test_rsi_downtrend_is_low(self):
        """持续下跌 → RSI 应接近 0"""
        prices = pd.Series([float(30 - i) for i in range(30)])  # 30,29,...,1
        rsi = _compute_rsi(prices)
        assert rsi is not None
        last = float(rsi.iloc[-1])
        assert last < 30, f"下跌趋势 RSI 应 < 30, 实际 {last}"

    def test_rsi_insufficient_data(self):
        """数据不足时返回 None"""
        prices = pd.Series([1.0, 2.0, 3.0])  # 只有 3 天
        rsi = _compute_rsi(prices)
        assert rsi is None

    def test_macd_uptrend(self):
        """上涨趋势 → MACD > 0, 柱状图 > 0"""
        prices = pd.Series([float(i) for i in range(1, 51)])  # 50 天上涨
        result = _compute_macd(prices)
        assert result is not None
        macd_line, signal_line, histogram = result
        assert float(macd_line.iloc[-1]) > 0
        assert float(histogram.iloc[-1]) > 0

    def test_macd_insufficient_data(self):
        """数据不足时返回 None"""
        prices = pd.Series([1.0, 2.0] * 5)  # 只有 10 天
        result = _compute_macd(prices)
        assert result is None

    def test_bb_bands_ordered(self):
        """布林带上轨 > 中轨 > 下轨"""
        prices = pd.Series([float(100 + (i % 20 - 10)) for i in range(50)])
        result = _compute_bb(prices)
        assert result is not None
        upper, middle, lower = result
        assert float(upper.iloc[-1]) > float(middle.iloc[-1]) > float(lower.iloc[-1])


class TestTechnicalSignal:
    """技术信号集成测试"""

    def test_no_data_returns_empty(self, signal_conn):
        """无数据时返回空列表"""
        with patch("signals.technical.get_signal_db", return_value=signal_conn):
            signals = compute_technical()
        assert signals == []

    def test_rsi_signal_detected(self, signal_conn, populated_target):
        """RSI 信号被检测到"""
        tid, rid = 44992, 10000002
        # 插入下跌趋势数据 → RSI 低
        for i in range(50):
            price = float(500 - i * 8)  # 500 → 108 持续下跌
            signal_conn.execute(
                "INSERT INTO volume_snapshots (type_id, region_id, date, sell_price, buy_volume, sell_volume) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (tid, rid, f"2025-01-{i+1:02d}", price, 1000, 1000),
            )
        signal_conn.commit()

        with patch("signals.technical.get_signal_db", return_value=signal_conn):
            signals = compute_technical()

        rsi_signals = [s for s in signals if s.indicator == "RSI"]
        assert len(rsi_signals) >= 1
        assert any("超卖" in s.signal for s in rsi_signals)

    def test_macd_signal_detected(self, signal_conn, populated_target):
        """MACD 金叉信号检测"""
        tid, rid = 44992, 10000002
        # 价格: 15d平→15d跌→5d急跌→6d弹 → 金叉在最后5周期内发生
        prices = [500]*15 + [500-i*7 for i in range(15)] + [400-i*10 for i in range(5)] + [355+i*18 for i in range(6)]
        for i, price in enumerate(prices):
            signal_conn.execute(
                "INSERT INTO volume_snapshots (type_id, region_id, date, sell_price, buy_volume, sell_volume) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (tid, rid, f"2025-02-{i+1:02d}", price, 1000, 1000),
            )
        signal_conn.commit()

        with patch("signals.technical.get_signal_db", return_value=signal_conn):
            signals = compute_technical()

        macd_signals = [s for s in signals if s.indicator == "MACD"]
        assert len(macd_signals) >= 1

    def test_bb_signal_detected(self, signal_conn, populated_target):
        """布林带触轨信号检测"""
        tid, rid = 44992, 10000002
        # 29 天稳定 500, 最后 1 天跳升到 10000 → 超出上轨 (需>=30条)
        prices = [500.0] * 29 + [10000.0]
        for i, price in enumerate(prices):
            signal_conn.execute(
                "INSERT INTO volume_snapshots (type_id, region_id, date, sell_price, buy_volume, sell_volume) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (tid, rid, f"2025-03-{i+1:02d}", price, 1000, 1000),
            )
        signal_conn.commit()

        with patch("signals.technical.get_signal_db", return_value=signal_conn):
            signals = compute_technical()

        bb_signals = [s for s in signals if s.indicator == "BB"]
        assert len(bb_signals) >= 1
        assert any("上轨" in s.signal for s in bb_signals)
