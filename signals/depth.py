"""
深度不平衡信号 — 根据订单簿买卖挂单偏离统计基线发出反转信号

输入: signal.db depth_snapshots 表（最近 N 次深度快照）
输出: 深度信号列表
"""

import logging
import statistics
from dataclasses import dataclass

from eve_reuse.constants import HUB_NAMES
from signals.db import get_setting, get_signal_db, resolve_item_name

logger = logging.getLogger(__name__)

SignalLevel = str  # "无" | "轻度" | "强烈"


@dataclass
class DepthSignal:
    """一条深度信号"""
    type_id: int
    region_id: int
    item_name: str
    hub_name: str
    current_imbalance: float    # 当前不平衡比率 (bid/ask)
    historical_mean: float       # 历史均值
    deviation_sigma: float       # 偏离标准差倍数
    signal_level: SignalLevel    # 信号等级
    direction: str               # "看涨" | "看跌"


_N_WINDOW = 24  # 取最近 24 条快照


def compute_depth(sigma_threshold: float | None = None) -> list[DepthSignal]:
    """计算深度不平衡信号

    Args:
        sigma_threshold: 标准差倍数阈值，默认 2.0

    Returns:
        深度信号列表
    """
    if sigma_threshold is None:
        sigma_threshold = float(get_setting("depth_sigma", "2.0"))

    conn = get_signal_db()

    # 获取所有有深度数据的 (type_id, region_id)
    targets = conn.execute(
        """SELECT DISTINCT type_id, region_id FROM depth_snapshots"""
    ).fetchall()

    signals: list[DepthSignal] = []

    for row in targets:
        tid, rid = row["type_id"], row["region_id"]

        # 取最近 N 条
        snapshots = conn.execute(
            """SELECT imbalance_ratio, fetch_time
               FROM depth_snapshots
               WHERE type_id = ? AND region_id = ?
               ORDER BY fetch_time DESC LIMIT ?""",
            (tid, rid, _N_WINDOW),
        ).fetchall()

        if len(snapshots) < 4:
            continue

        ratios = [s["imbalance_ratio"] or 1.0 for s in snapshots]
        current = ratios[0]  # 最新一条

        mean = statistics.mean(ratios)
        stdev = statistics.stdev(ratios) if len(ratios) > 1 else 1.0
        sigma = (current - mean) / stdev if stdev > 0 else 0.0

        # 判断信号强度
        abs_sigma = abs(sigma)
        if abs_sigma >= sigma_threshold * 1.5:
            level: SignalLevel = "强烈"
        elif abs_sigma >= sigma_threshold:
            level = "轻度"
        else:
            level = "无"

        if level != "无":
            direction = "看涨" if sigma > 0 else "看跌"
            name = resolve_item_name(tid)
            hub = HUB_NAMES.get(rid, str(rid))
            signals.append(DepthSignal(
                type_id=tid,
                region_id=rid,
                item_name=name,
                hub_name=hub,
                current_imbalance=round(current, 3),
                historical_mean=round(mean, 3),
                deviation_sigma=round(sigma, 2),
                signal_level=level,
                direction=direction,
            ))

    signals.sort(key=lambda s: abs(s.deviation_sigma), reverse=True)
    logger.info("深度信号: 发现 %d 个信号 (σ阈值 %.1f)", len(signals), sigma_threshold)
    return signals
