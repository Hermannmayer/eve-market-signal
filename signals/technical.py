"""
技术指标信号 — 基于 pandas 的 RSI / MACD / 布林带分析

输入: signal.db volume_snapshots 表（最近 60 天价格数据）
输出: 技术指标信号列表

新依赖: pandas (纯 Python 实现指标，无需 pandas-ta/numba)
"""

import logging
from dataclasses import dataclass

import pandas as pd

from eve_reuse.constants import HUB_NAMES
from signals.db import get_signal_db, resolve_item_name

logger = logging.getLogger(__name__)


# ── 信号定义 ──────────────────────────────────────────

@dataclass
class TechnicalSignal:
    """一条技术指标信号"""
    type_id: int
    region_id: int
    item_name: str
    hub_name: str
    indicator: str      # "RSI" | "MACD" | "BB"
    value: float         # 当前指标值
    signal: str          # 信号描述
    level: str           # "强烈" | "轻度" | "无"


# ── 指标计算（纯 pandas，无外部依赖） ──────────────────


def _compute_rsi(prices: pd.Series, length: int = 14) -> pd.Series | None:
    """计算 RSI（相对强弱指标）"""
    if len(prices) < length + 1:
        return None
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(span=length, adjust=False).mean()
    avg_loss = loss.ewm(span=length, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def _compute_macd(
    prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series] | None:
    """计算 MACD 线、信号线、柱状图"""
    if len(prices) < slow + signal:
        return None
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _compute_bb(
    prices: pd.Series, length: int = 20, std: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series] | None:
    """计算布林带上/中/下轨"""
    if len(prices) < length:
        return None
    middle = prices.rolling(length).mean()
    std_dev = prices.rolling(length).std()
    upper = middle + std * std_dev
    lower = middle - std * std_dev
    return upper, middle, lower


# ── 信号判断 ──────────────────────────────────────────


def _rsi_signals(
    rsi_series: pd.Series, item_name: str, hub: str,
    tid: int, rid: int,
) -> list[TechnicalSignal]:
    """从 RSI 序列生成信号"""
    signals: list[TechnicalSignal] = []
    if rsi_series is None or rsi_series.isna().all():
        return signals
    current = float(rsi_series.iloc[-1])
    prev = float(rsi_series.iloc[-2]) if len(rsi_series) > 1 else current

    if current <= 30:
        signals.append(TechnicalSignal(
            type_id=tid, region_id=rid,
            item_name=item_name, hub_name=hub,
            indicator="RSI",
            value=round(current, 1),
            signal=f"超卖反弹 (RSI={current:.0f})",
            level="强烈" if current <= 25 else "轻度",
        ))
    elif current >= 70:
        signals.append(TechnicalSignal(
            type_id=tid, region_id=rid,
            item_name=item_name, hub_name=hub,
            indicator="RSI",
            value=round(current, 1),
            signal=f"超买回调 (RSI={current:.0f})",
            level="强烈" if current >= 75 else "轻度",
        ))

    # RSI 背离检测
    if len(rsi_series) >= 5:
        rsi_5d_ago = float(rsi_series.iloc[-5])
        if current > rsi_5d_ago + 10 and prev <= 30 < current:
            signals.append(TechnicalSignal(
                type_id=tid, region_id=rid,
                item_name=item_name, hub_name=hub,
                indicator="RSI",
                value=round(current, 1),
                signal="RSI 底背离 → 看涨",
                level="轻度",
            ))
        elif current < rsi_5d_ago - 10 and prev >= 70 > current:
            signals.append(TechnicalSignal(
                type_id=tid, region_id=rid,
                item_name=item_name, hub_name=hub,
                indicator="RSI",
                value=round(current, 1),
                signal="RSI 顶背离 → 看跌",
                level="轻度",
            ))

    return signals


def _macd_signals(
    macd_line: pd.Series, signal_line: pd.Series, histogram: pd.Series,
    item_name: str, hub: str, tid: int, rid: int,
) -> list[TechnicalSignal]:
    """从 MACD 生成信号 (金叉/死叉)，扫描最近 5 个周期"""
    signals: list[TechnicalSignal] = []
    if macd_line is None or len(macd_line) < 2:
        return signals

    # 扫描最后 5 个周期（含当前）查找交叉
    n = min(5, len(macd_line) - 1)
    for i in range(len(macd_line) - n, len(macd_line)):
        prev_m = float(macd_line.iloc[i - 1])
        curr_m = float(macd_line.iloc[i])
        prev_s = float(signal_line.iloc[i - 1])
        curr_s = float(signal_line.iloc[i])
        prev_h = float(histogram.iloc[i - 1])
        curr_h = float(histogram.iloc[i])

        # 金叉: MACD 上穿信号线
        if prev_m <= prev_s and curr_m > curr_s:
            signals.append(TechnicalSignal(
                type_id=tid, region_id=rid,
                item_name=item_name, hub_name=hub,
                indicator="MACD",
                value=round(curr_m, 2),
                signal="MACD 金叉 → 看涨",
                level="轻度",
            ))

        # 死叉: MACD 下穿信号线
        if prev_m >= prev_s and curr_m < curr_s:
            signals.append(TechnicalSignal(
                type_id=tid, region_id=rid,
                item_name=item_name, hub_name=hub,
                indicator="MACD",
                value=round(curr_m, 2),
                signal="MACD 死叉 → 看跌",
                level="轻度",
            ))

        # 柱状图转正
        if prev_h <= 0 < curr_h:
            signals.append(TechnicalSignal(
                type_id=tid, region_id=rid,
                item_name=item_name, hub_name=hub,
                indicator="MACD",
                value=round(curr_h, 2),
                signal="MACD 柱转正 → 动能转强",
                level="轻度",
            ))

        # 柱状图转负
        if prev_h >= 0 > curr_h:
            signals.append(TechnicalSignal(
                type_id=tid, region_id=rid,
                item_name=item_name, hub_name=hub,
                indicator="MACD",
                value=round(curr_h, 2),
                signal="MACD 柱转负 → 动能转弱",
                level="轻度",
            ))

    return signals


def _bb_signals(
    upper: pd.Series, middle: pd.Series, lower: pd.Series,
    prices: pd.Series, item_name: str, hub: str, tid: int, rid: int,
) -> list[TechnicalSignal]:
    """从布林带生成信号 (触轨/突破)"""
    signals: list[TechnicalSignal] = []
    if upper is None or len(upper) < 1:
        return signals

    curr_price = float(prices.iloc[-1])
    curr_upper = float(upper.iloc[-1])
    curr_lower = float(lower.iloc[-1])
    curr_mid = float(middle.iloc[-1])
    band_width = ((curr_upper - curr_lower) / curr_mid * 100) if curr_mid else 0

    if curr_price >= curr_upper:
        signals.append(TechnicalSignal(
            type_id=tid, region_id=rid,
            item_name=item_name, hub_name=hub,
            indicator="BB",
            value=round(band_width, 1),
            signal="触及上轨 → 可能回调",
            level="轻度",
        ))
    elif curr_price <= curr_lower:
        signals.append(TechnicalSignal(
            type_id=tid, region_id=rid,
            item_name=item_name, hub_name=hub,
            indicator="BB",
            value=round(band_width, 1),
            signal="触及下轨 → 可能反弹",
            level="轻度",
        ))

    # 带宽收窄 → 即将突破
    if len(upper) >= 10:
        bw_10d_ago = ((float(upper.iloc[-10]) - float(lower.iloc[-10])) / float(middle.iloc[-10]) * 100)
        if bw_10d_ago > 0 and band_width < bw_10d_ago * 0.7:
            signals.append(TechnicalSignal(
                type_id=tid, region_id=rid,
                item_name=item_name, hub_name=hub,
                indicator="BB",
                value=round(band_width, 1),
                signal="布林带收窄 → 即将突破",
                level="轻度",
            ))

    return signals


# ── 主入口 ──────────────────────────────────────────


def compute_technical() -> list[TechnicalSignal]:
    """计算所有 watch_targets 的技术指标信号"""
    conn = get_signal_db()

    targets = conn.execute(
        """SELECT DISTINCT w.type_id, w.region_id
           FROM watch_targets w
           INNER JOIN volume_snapshots v
               ON w.type_id = v.type_id AND w.region_id = v.region_id
           WHERE w.enabled = 1"""
    ).fetchall()

    if not targets:
        logger.info("没有启用的监控目标，跳过技术信号")
        return []

    all_signals: list[TechnicalSignal] = []
    logger.info("计算 %d 个目标的技术指标", len(targets))

    for row in targets:
        tid, rid = row["type_id"], row["region_id"]

        rows = conn.execute(
            """SELECT date, sell_price
               FROM volume_snapshots
               WHERE type_id = ? AND region_id = ?
               ORDER BY date ASC""",
            (tid, rid),
        ).fetchall()

        if len(rows) < 30:
            continue

        prices = pd.Series(
            [float(r["sell_price"] or 0) for r in rows],
            name="close",
        )
        # 剔除 0 值
        prices = prices[prices > 0]
        if len(prices) < 30:
            continue

        name = resolve_item_name(tid)
        hub = HUB_NAMES.get(rid, str(rid))

        # RSI
        rsi = _compute_rsi(prices)
        if rsi is not None:
            all_signals.extend(_rsi_signals(rsi, name, hub, tid, rid))

        # MACD
        macd_result = _compute_macd(prices)
        if macd_result is not None:
            macd_line, signal_line, histogram = macd_result
            all_signals.extend(_macd_signals(
                macd_line, signal_line, histogram, name, hub, tid, rid,
            ))

        # Bollinger Bands
        bb_result = _compute_bb(prices)
        if bb_result is not None:
            upper, middle, lower = bb_result
            all_signals.extend(_bb_signals(
                upper, middle, lower, prices, name, hub, tid, rid,
            ))

    all_signals.sort(key=lambda s: s.indicator)
    logger.info("技术信号: 发现 %d 个信号", len(all_signals))
    return all_signals
