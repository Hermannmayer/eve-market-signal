"""
订单簿深度拉取 — 从 ESI 获取每个 watch_target 的前 10 档买卖单

ESI: GET /markets/{region_id}/orders/?type_id={type_id}&order_type=all

写入 signal.db depth_snapshots 表，供 signals/depth.py 消费。
"""

import asyncio
import json
import logging

from fetch.esi_client import ESIClient
from signals.db import get_signal_db

logger = logging.getLogger(__name__)

client = ESIClient(concurrency=10)


def _get_watch_targets() -> list[tuple[int, int, str]]:
    """获取所有启用的监控目标 (type_id, region_id, label)"""
    conn = get_signal_db()
    rows = conn.execute(
        "SELECT type_id, region_id, label FROM watch_targets WHERE enabled = 1"
    ).fetchall()
    return [(r["type_id"], r["region_id"], r["label"] or "") for r in rows]


async def _fetch_depth(type_id: int, region_id: int) -> dict | None:
    """拉取单个物品单个区域的订单簿深度

    聚合前 10 档买单和前 10 档卖单
    """
    path = f"/markets/{region_id}/orders/?type_id={type_id}&order_type=all"
    data = await client.fetch(path)
    if not isinstance(data, list) or not data:
        return None

    bids: list[tuple[float, float]] = []  # (price, volume_remain)
    asks: list[tuple[float, float]] = []
    bid_vol_total = 0.0
    ask_vol_total = 0.0

    for order in data:
        price = order["price"]
        vol = order["volume_remain"]
        if order["is_buy_order"]:
            bids.append((price, vol))
            bid_vol_total += vol
        else:
            asks.append((price, vol))
            ask_vol_total += vol

    # 排序：买单降序（最高价在前），卖单升序（最低价在前）
    bids.sort(key=lambda x: x[0], reverse=True)
    asks.sort(key=lambda x: x[0])

    top10_bids = bids[:10]
    top10_asks = asks[:10]

    best_bid = bids[0][0] if bids else 0.0
    best_ask = asks[0][0] if asks else 0.0
    mid_price = (best_bid + best_ask) / 2 if best_bid and best_ask else 0.0
    spread_isk = best_ask - best_bid if best_ask and best_bid else 0.0
    spread_pct = (spread_isk / mid_price * 100) if mid_price else 0.0
    imbalance_ratio = (bid_vol_total / ask_vol_total) if ask_vol_total else 0.0

    return {
        "mid_price": mid_price,
        "spread_isk": spread_isk,
        "spread_pct": spread_pct,
        "bid_total_volume": bid_vol_total,
        "ask_total_volume": ask_vol_total,
        "imbalance_ratio": imbalance_ratio,
        "top10_bids": json.dumps(top10_bids),
        "top10_asks": json.dumps(top10_asks),
    }


async def fetch_depth(targets: list[tuple[int, int]] | None = None):
    """拉取订单簿深度并写入 depth_snapshots

    Args:
        targets: [(type_id, region_id)]，None 表示所有 watch_targets
    """
    if targets is None:
        targets = [(tid, rid) for tid, rid, _ in _get_watch_targets()]

    if not targets:
        logger.info("没有启用的监控目标，跳过深度拉取")
        return

    logger.info("开始拉取 %d 个目标的深度数据", len(targets))

    conn = get_signal_db()
    total = 0
    for tid, rid in targets:
        result = await _fetch_depth(tid, rid)
        if result is None:
            continue

        conn.execute(
            """INSERT INTO depth_snapshots
               (type_id, region_id, fetch_time, mid_price, spread_isk, spread_pct,
                bid_total_volume, ask_total_volume, imbalance_ratio,
                top10_bids, top10_asks)
               VALUES (?, ?, datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                tid, rid,
                result["mid_price"], result["spread_isk"], result["spread_pct"],
                result["bid_total_volume"], result["ask_total_volume"],
                result["imbalance_ratio"],
                result["top10_bids"], result["top10_asks"],
            ),
        )
        total += 1

    conn.commit()
    logger.info("深度拉取完成: %d 个目标", total)


def run_depth_update():
    """同步入口"""
    asyncio.run(fetch_depth())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_depth_update()
