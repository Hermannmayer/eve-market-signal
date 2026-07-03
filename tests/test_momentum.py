"""
量价趋势信号测试
"""

from unittest.mock import patch

from signals.momentum import _classify, compute_momentum


class TestMomentumComputation:
    """量价趋势信号计算测试"""

    def test_no_data_returns_empty(self, signal_conn):
        """无数据时返回空列表"""
        with patch("signals.momentum.get_signal_db", return_value=signal_conn):
            signals = compute_momentum(volume_ratio_threshold=2.0, price_ratio_threshold=1.05)
        assert signals == []

    def test_momentum_detection(self, signal_conn, populated_volume, populated_target):
        """验证放量上涨信号检测"""
        with patch("signals.momentum.get_signal_db", return_value=signal_conn):
            signals = compute_momentum(volume_ratio_threshold=1.5, price_ratio_threshold=1.02)

        assert len(signals) >= 1
        sig = signals[0]
        assert sig.volume_ratio > 1.5
        assert sig.price_ratio > 1.02

    def test_momentum_low_threshold_returns_more(self, signal_conn, populated_volume, populated_target):
        """降低阈值应返回更多信号"""
        with patch("signals.momentum.get_signal_db", return_value=signal_conn):
            strict = compute_momentum(volume_ratio_threshold=10, price_ratio_threshold=2.0)
            loose = compute_momentum(volume_ratio_threshold=1.1, price_ratio_threshold=1.01)
        assert len(loose) >= len(strict)

    def test_classify_volume_breakout(self):
        """放量上涨分类"""
        result = _classify(2.5, 1.10, 2.0, 1.05)
        assert result == "放量上涨"

    def test_classify_no_signal(self):
        """正常波动无信号"""
        result = _classify(1.0, 1.0, 2.0, 1.05)
        assert result is None

    def test_classify_decline(self):
        """放量下跌"""
        result = _classify(2.5, 0.90, 2.0, 1.05)
        assert result == "放量下跌"
