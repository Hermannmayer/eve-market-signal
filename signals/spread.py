"""
跨区域价差信号 — 四大贸易中心间的最优买卖价差套利信号

输入: signal.db market_prices 表（4 个区域的最优买卖价）
输出: 利润率超过阈值的套利机会列表
"""

import logging
from dataclasses import dataclass

from eve_reuse.constants import HUB_NAMES, TRADE_HUB_IDS
from signals.db import get_setting, get_signal_db, resolve_item_name

logger = logging.getLogger(__name__)


@dataclass
class SpreadSignal:
    """一条价差信号"""
    type_id: int
    item_name: str
    buy_hub: str          # 买入区域名
    sell_hub: str         # 卖出区域名
    buy_price: float      # 买入价
    sell_price: float     # 卖出价
    per_unit_profit: float  # 单件利润
    profit_margin: float  # 利润率 (%)
    trade_volume: int     # 可交易量（买卖成交量取小）
    total_profit: float   # 总利润


# 各区域间估计运费（ISK/件，基于常见货运价格）
# 来源: EVE 公开货运频道 Red Frog / PushX 估算
_ESTIMATED_FREIGHT: dict[tuple[str, str], float] = {
    ("Jita", "Amarr"): 1000,
    ("Jita", "Dodixie"): 500,
    ("Jita", "Rens"): 600,
    ("Amarr", "Jita"): 1000,
    ("Amarr", "Dodixie"): 800,
    ("Amarr", "Rens"): 700,
    ("Dodixie", "Jita"): 500,
    ("Dodixie", "Amarr"): 800,
    ("Dodixie", "Rens"): 600,
    ("Rens", "Jita"): 600,
    ("Rens", "Amarr"): 700,
    ("Rens", "Dodixie"): 600,
}


def _calc_profit(
    buy_price: float,
    sell_price: float,
    volume: int,
    buy_hub: str,
    sell_hub: str,
) -> tuple[float, float, float]:
    """计算净利润和利润率

    公式:
        毛利润 = (sell_price - buy_price) * volume
        运费 = _ESTIMATED_FREIGHT[(buy_hub, sell_hub)] * volume
        经纪人费 = buy_price * volume * 0.01 (假设 0 声望)
        销售税 = sell_price * volume * 0.02 (基础税率)
        净利润 = 毛利润 - 运费 - 经纪人费 - 销售税
        利润率 = 净利润 / (buy_price * volume + 运费) * 100
    """
    gross = (sell_price - buy_price) * volume
    freight = _ESTIMATED_FREIGHT.get((buy_hub, sell_hub), 800) * volume
    broker = buy_price * volume * 0.01
    tax = sell_price * volume * 0.02
    net = gross - freight - broker - tax
    cost = buy_price * volume + freight
    margin = (net / cost * 100) if cost > 0 else 0.0
    return net, margin, volume


def compute_spreads(min_margin: float | None = None) -> list[SpreadSignal]:
    """计算跨区域价差信号

    Args:
        min_margin: 最低利润率 (%)，默认从 settings.db 读取

    Returns:
        按利润率降序排列的信号列表
    """
    if min_margin is None:
        min_margin = float(get_setting("min_profit_margin", "10"))

    conn = get_signal_db()
    hub_ids = list(TRADE_HUB_IDS.values())

    # 获取所有有数据的 type_id
    tids = conn.execute(
        """SELECT DISTINCT type_id FROM market_prices
           WHERE region_id IN ({})""".format(
            ",".join("?" * len(hub_ids))
        ),
        hub_ids,
    ).fetchall()

    signals: list[SpreadSignal] = []

    for (tid,) in tids:
        # 每个 type_id 在 4 个区域的数据
        rows = conn.execute(
            """SELECT region_id, buy_price, sell_price, buy_volume, sell_volume
               FROM market_prices
               WHERE type_id = ? AND region_id IN ({})
               ORDER BY region_id""".format(
                ",".join("?" * len(hub_ids))
            ),
            [tid, *hub_ids],
        ).fetchall()

        # 找最优买入区域（最低卖价）和最优卖出区域（最高买价）
        best_buy_hub = None
        best_sell_hub = None
        best_buy_price = float("inf")
        best_sell_price = 0.0
        buy_vol = 0
        sell_vol = 0

        for row in rows:
            rid = row["region_id"]
            sell_p = row["sell_price"] or 0.0
            buy_p = row["buy_price"] or 0.0

            if sell_p > 0 and sell_p < best_buy_price:
                best_buy_price = sell_p
                best_buy_hub = HUB_NAMES.get(rid)
                buy_vol = row["buy_volume"] or 0

            if buy_p > best_sell_price:
                best_sell_price = buy_p
                best_sell_hub = HUB_NAMES.get(rid)
                sell_vol = row["sell_volume"] or 0

        if not best_buy_hub or not best_sell_hub or best_buy_hub == best_sell_hub:
            continue

        volume = min(buy_vol, sell_vol)
        net_profit, margin, trade_vol = _calc_profit(
            best_buy_price, best_sell_price, volume,
            best_buy_hub, best_sell_hub,
        )

        if margin >= min_margin and trade_vol > 0:
            name = resolve_item_name(tid)
            signals.append(SpreadSignal(
                type_id=tid,
                item_name=name,
                buy_hub=best_buy_hub,
                sell_hub=best_sell_hub,
                buy_price=best_buy_price,
                sell_price=best_sell_price,
                per_unit_profit=best_sell_price - best_buy_price,
                profit_margin=round(margin, 2),
                trade_volume=trade_vol,
                total_profit=round(net_profit, 2),
            ))

    signals.sort(key=lambda s: s.profit_margin, reverse=True)
    logger.info("价差信号: 发现 %d 个机会 (阈值 %.1f%%)", len(signals), min_margin)
    return signals
