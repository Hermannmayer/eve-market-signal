"""
深度不平衡信号测试
"""

from unittest.mock import patch

from signals.depth import compute_depth


class TestDepthComputation:
    """深度不平衡信号计算测试"""

    def test_no_data_returns_empty(self, signal_conn):
        """无深度数据时返回空列表"""
        with patch("signals.depth.get_signal_db", return_value=signal_conn):
            signals = compute_depth(sigma_threshold=2.0)
        assert signals == []

    def test_anomaly_detection(self, signal_conn, populated_depth):
        """异常不平衡被检测为信号"""
        with patch("signals.depth.get_signal_db", return_value=signal_conn):
            signals = compute_depth(sigma_threshold=1.5)

        assert len(signals) >= 1
        # 最后一条 imbalance=3.5, 均值约 1.0, 应该被检测到
        sig = signals[0]
        assert sig.deviation_sigma > 1.5

    def test_high_threshold_filters(self, signal_conn, populated_depth):
        """高 sigma 阈值过滤掉弱信号"""
        with patch("signals.depth.get_signal_db", return_value=signal_conn):
            signals = compute_depth(sigma_threshold=10)
        assert signals == []
