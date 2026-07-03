"""
跨区域价差信号测试
"""

from unittest.mock import patch

from signals.spread import compute_spreads


class TestSpreadComputation:
    """价差信号计算测试"""

    def test_no_data_returns_empty(self, signal_conn):
        """无市场数据时返回空列表"""
        with patch("signals.spread.get_signal_db", return_value=signal_conn):
            signals = compute_spreads(min_margin=10)
        assert signals == []

    def test_spread_detection(self, signal_conn, populated_market_prices):
        """验证跨区域价差检测"""
        with patch("signals.spread.get_signal_db", return_value=signal_conn):
            signals = compute_spreads(min_margin=1)

        assert len(signals) >= 1
        # type_id=2 有宽价差（Rens sell=200 → Jita buy=5000 → 4800/件利润）
        signals_by_tid = {s.type_id: s for s in signals}
        assert 2 in signals_by_tid
        assert signals_by_tid[2].profit_margin > 0

    def test_min_margin_filter(self, signal_conn, populated_market_prices):
        """验证最低利润率过滤"""
        with patch("signals.spread.get_signal_db", return_value=signal_conn):
            signals_high = compute_spreads(min_margin=1000)
        assert signals_high == []

    def test_profit_calculation(self):
        """验证利润计算逻辑"""
        from signals.spread import _calc_profit

        # Rens→Jita: freight=600, buy=100 sell=5000, volume=10
        net, margin, vol = _calc_profit(100, 5000, 10, "Rens", "Jita")
        assert vol == 10
        # 毛利润=(5000-100)*10=49000, 运费=6000, 经纪费=10, 税=1000
        # 净利润=49000-6000-10-1000=41990
        assert net > 0
        assert margin > 10  # 利润率超过 10%
