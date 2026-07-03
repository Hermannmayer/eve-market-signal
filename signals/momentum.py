"""
量价趋势信号 — 基于历史成交量的放量突破/缩量阴跌/趋势背离

输入: signal.db volume_snapshots 表（最近 30 天数据）
输出: 趋势信号列表
"""

import logging
from dataclasses import dataclass

from eve_reuse.constants import HUB_NAMES
from signals.db import get_setting, get_signal_db, resolve_item_name

logger = logging.getLogger(__name__)

SignalLabel = str  # "放量上涨" | "放量下跌" | "缩量阴跌" | "无量上涨"


@dataclass
class MomentumSignal:
    """一条趋势信号"""
    type_id: int
    region_id: int
    item_name: str
    hub_name: str
    label: SignalLabel
    volume_ratio: float      # 量比: 近7日均量 / 近30日均量
    price_ratio: float       # 价比: 当前价 / 30日均价
    avg_volume_7d: float     # 近7日均量
    avg_volume_30d: float    # 近30日均量
    current_price: float     # 当前价


def compute_momentum(
    volume_ratio_threshold: float | None = None,
    price_ratio_threshold: float | None = None,
) -> list[MomentumSignal]:
    """计算量价趋势信号

    Args:
        volume_ratio_threshold: 量比阈值，默认 2.0
        price_ratio_threshold: 价比阈值，默认 1.05

    Returns:
        信号列表
    """
    if volume_ratio_threshold is None:
        volume_ratio_threshold = float(get_setting("mom_volume_ratio", "2.0"))
    if price_ratio_threshold is None:
        price_ratio_threshold = float(get_setting("mom_price_ratio", "1.05"))

    conn = get_signal_db()

    # 获取有监控目标且有历史数据的 (type_id, region_id)
    targets = conn.execute(
        """SELECT DISTINCT w.type_id, w.region_id
           FROM watch_targets w
           INNER JOIN volume_snapshots v ON w.type_id = v.type_id AND w.region_id = v.region_id
           WHERE w.enabled = 1"""
    ).fetchall()

    signals: list[MomentumSignal] = []

    for row in targets:
        tid, rid = row["type_id"], row["region_id"]

        # 取最近 30 天
        history = conn.execute(
            """SELECT date, sell_price, buy_volume, sell_volume
               FROM volume_snapshots
               WHERE type_id = ? AND region_id = ?
               ORDER BY date DESC LIMIT 30""",
            (tid, rid),
        ).fetchall()

        if len(history) < 7:
            continue

        # 计算量价指标
        total_volume_7d = 0.0
        total_volume_30d = 0.0
        total_price_30d = 0.0

        for i, h in enumerate(history):
            vol = (h["buy_volume"] or 0) + (h["sell_volume"] or 0)
            price = h["sell_price"] or 0
            if i < 7:
                total_volume_7d += vol
            total_volume_30d += vol
            total_price_30d += price

        avg_vol_7d = total_volume_7d / 7
        avg_vol_30d = total_volume_30d / min(len(history), 30)
        avg_price_30d = total_price_30d / min(len(history), 30) if history else 0

        if avg_vol_30d <= 0 or avg_price_30d <= 0:
            continue

        v_ratio = avg_vol_7d / avg_vol_30d
        p_ratio = history[0]["sell_price"] / avg_price_30d if avg_price_30d else 1.0

        # 分类
        label = _classify(v_ratio, p_ratio, volume_ratio_threshold, price_ratio_threshold)
        if label:
            name = resolve_item_name(tid)
            hub = HUB_NAMES.get(rid, str(rid))
            signals.append(MomentumSignal(
                type_id=tid,
                region_id=rid,
                item_name=name,
                hub_name=hub,
                label=label,
                volume_ratio=round(v_ratio, 3),
                price_ratio=round(p_ratio, 3),
                avg_volume_7d=round(avg_vol_7d, 1),
                avg_volume_30d=round(avg_vol_30d, 1),
                current_price=history[0]["sell_price"] or 0.0,
            ))

    logger.info("趋势信号: 发现 %d 个信号", len(signals))
    return signals


def _classify(v_ratio: float, p_ratio: float, vol_thresh: float, price_thresh: float) -> SignalLabel | None:
    """根据量价比分类"""
    if v_ratio > vol_thresh and p_ratio > price_thresh:
        return "放量上涨"
    if v_ratio > vol_thresh and p_ratio < (2 - price_thresh):
        return "放量下跌"
    if v_ratio < 0.5 and p_ratio < 0.90:
        return "缩量阴跌"
    if p_ratio > 1.10 and v_ratio < 1.5:
        return "无量上涨"
    return None
