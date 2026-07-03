"""
市场价格拉取 — 从 ESI 获取四大贸易中心基准价 + 订单簿

流程:
  1. GET /markets/prices/  → 全局均价（兜底）
  2. GET /markets/{rid}/orders/ → 各贸易中心订单簿
  3. 合并写入 signal.db market_prices 表
"""

import asyncio
import logging

import aiohttp

from eve_reuse.constants import TRADE_HUB_IDS
from fetch.esi_client import ESIClient
from signals.db import get_signal_db

logger = logging.getLogger(__name__)

client = ESIClient(concurrency=50)


def _hub_region_ids() -> list[int]:
    return list(TRADE_HUB_IDS.values())


# ── 第一阶段: 基准价 ──────────────────────────────────


async def _fetch_baseline() -> dict[int, dict]:
    """GET /markets/prices/  → {type_id: {buy, sell}}"""
    data = await client.fetch("/markets/prices/")
    if not data:
        logger.warning("基准价接口返回空")
        return {}

    result: dict[int, dict] = {}
    for entry in data:
        tid = entry["type_id"]
        result[tid] = {
            "buy_price": entry.get("average_price", 0) or 0,
            "sell_price": entry.get("adjusted_price", 0) or 0,
        }
    logger.info("基准价: %d 个物品", len(result))
    return result


# ── 第二阶段: 订单簿 ──────────────────────────────────


async def _discover_pages(region_id: int, order_type: str) -> int:
    """探测订单簿总页数"""
    path = f"/markets/{region_id}/orders/?order_type={order_type}&page=1"
    url = f"https://esi.evetech.net/latest/{path.lstrip('/')}"
    try:
        async with client._semaphore:
            async with aiohttp.ClientSession(
                headers=client._headers, timeout=client._timeout
            ) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return 0
                    header = resp.headers.get("X-Pages", "1")
                    return int(header)
    except Exception:
        logger.exception("探测页数失败: region=%d type=%s", region_id, order_type)
        return 0


async def _fetch_orders_page(region_id: int, order_type: str, page: int) -> list:
    """拉取单页订单数据"""
    path = f"/markets/{region_id}/orders/?order_type={order_type}&page={page}"
    data = await client.fetch(path)
    return data if isinstance(data, list) else []


async def _fetch_region_orders(region_id: int) -> dict[int, dict]:
    """拉取一个区域的买卖订单"""
    buy_pages = await _discover_pages(region_id, "buy")
    sell_pages = await _discover_pages(region_id, "sell")

    logger.info("区域 %d: buy=%d页 sell=%d页", region_id, buy_pages, sell_pages)

    # 并发拉取所有页
    tasks = []
    for order_type, pages in [("buy", buy_pages), ("sell", sell_pages)]:
        for p in range(1, pages + 1):
            tasks.append(_fetch_orders_page(region_id, order_type, p))

    results = await asyncio.gather(*tasks) if tasks else []

    # 聚合
    buy_map: dict[int, float] = {}  # type_id → max buy price
    sell_map: dict[int, float] = {}  # type_id → min sell price
    buy_vol: dict[int, int] = {}
    sell_vol: dict[int, int] = {}

    for page_data in results:
        if not page_data:
            continue
        for order in page_data:
            tid = order["type_id"]
            price = order["price"]
            vol_remain = order["volume_remain"]
            if order["is_buy_order"]:
                if tid not in buy_map or price > buy_map[tid]:
                    buy_map[tid] = price
                buy_vol[tid] = buy_vol.get(tid, 0) + vol_remain
            else:
                if tid not in sell_map or price < sell_map[tid]:
                    sell_map[tid] = price
                sell_vol[tid] = sell_vol.get(tid, 0) + vol_remain

    all_tids = set(buy_map) | set(sell_map)
    result = {}
    for tid in all_tids:
        result[tid] = {
            "buy_price": buy_map.get(tid, 0.0),
            "sell_price": sell_map.get(tid, 0.0),
            "buy_volume": buy_vol.get(tid, 0),
            "sell_volume": sell_vol.get(tid, 0),
        }
    logger.info("区域 %d: %d 个物品有订单数据", region_id, len(result))
    return result


# ── 写入数据库 ──────────────────────────────────────────


def _save_prices(region_id: int, prices: dict[int, dict]):
    """写入 market_prices 表"""
    conn = get_signal_db()
    conn.execute("DELETE FROM market_prices WHERE region_id = ?", (region_id,))

    rows = [
        (tid, region_id, p["buy_price"], p["sell_price"], p["buy_volume"], p["sell_volume"])
        for tid, p in prices.items()
    ]

    BATCH = 500
    for i in range(0, len(rows), BATCH):
        batch = rows[i : i + BATCH]
        conn.executemany(
            """INSERT INTO market_prices
               (type_id, region_id, buy_price, sell_price, buy_volume, sell_volume)
               VALUES (?, ?, ?, ?, ?, ?)""",
            batch,
        )
    conn.commit()
    logger.info("写入 market_prices: 区域 %d → %d 条", region_id, len(rows))


# ── 主入口 ──────────────────────────────────────────


async def fetch_market_prices(regions: list[str] | None = None):
    """主入口：拉取市场价并写入数据库

    Args:
        regions: 区域名列表，如 ["Jita", "Amarr"]，None 表示全部 4 个中心
    """
    target_ids = []
    if regions:
        for name in regions:
            rid = TRADE_HUB_IDS.get(name)
            if rid:
                target_ids.append(rid)
        if not target_ids:
            logger.warning("未找到有效的区域名: %s", regions)
            return
    else:
        target_ids = _hub_region_ids()

    logger.info("开始拉取市场价: 区域=%s", target_ids)

    # 基准价
    baseline = await _fetch_baseline()

    # 各区域订单簿
    for rid in target_ids:
        orders = await _fetch_region_orders(rid)

        # 订单数据覆盖基准价
        merged = dict(baseline)
        for tid, odata in orders.items():
            merged[tid] = odata

        _save_prices(rid, merged)

    logger.info("市场价拉取完成")


def run_price_update(regions: list[str] | None = None):
    """同步入口"""
    asyncio.run(fetch_market_prices(regions))
