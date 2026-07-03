"""
历史量价拉取 — 从 ESI 获取每个 watch_target 的历史日数据

ESI: GET /markets/{region_id}/history/?type_id={type_id}
"""

import asyncio
import logging

from fetch.esi_client import ESIClient
from signals.db import get_signal_db

logger = logging.getLogger(__name__)

client = ESIClient(concurrency=10)


def _get_watch_type_regions() -> list[tuple[int, int]]:
    """获取所有启用的监控目标 (type_id, region_id)"""
    conn = get_signal_db()
    rows = conn.execute(
        "SELECT type_id, region_id FROM watch_targets WHERE enabled = 1"
    ).fetchall()
    return [(r["type_id"], r["region_id"]) for r in rows]


async def _fetch_history(type_id: int, region_id: int) -> list[dict]:
    """拉取单个物品单个区域的历史数据"""
    path = f"/markets/{region_id}/history/?type_id={type_id}"
    data = await client.fetch(path)
    return data if isinstance(data, list) else []


async def fetch_history(targets: list[tuple[int, int]] | None = None):
    """拉取历史量价并写入 volume_snapshots

    Args:
        targets: [(type_id, region_id)] 列表，None 表示拉所有启用的 watch_targets
    """
    if targets is None:
        targets = _get_watch_type_regions()

    if not targets:
        logger.info("没有启用的监控目标，跳过历史拉取")
        return

    logger.info("开始拉取 %d 个目标的历史量价", len(targets))
    results = await asyncio.gather(
        *[_fetch_history(tid, rid) for tid, rid in targets],
        return_exceptions=True,
    )

    conn = get_signal_db()
    total = 0
    for (tid, rid), history in zip(targets, results, strict=False):
        if isinstance(history, Exception):
            logger.warning("拉取历史失败: type_id=%d region=%d: %s", tid, rid, history)
            continue
        if not history:
            continue

        # 覆盖写入
        conn.execute(
            "DELETE FROM volume_snapshots WHERE type_id = ? AND region_id = ?",
            (tid, rid),
        )

        rows = []
        for entry in history:
            rows.append((
                tid, rid, entry["date"],
                entry.get("average", 0) or 0,
                entry.get("highest", 0) or 0,
                entry.get("lowest", 0) or 0,
                entry.get("volume", 0) or 0,
                entry.get("order_count", 0) or 0,
            ))

        BATCH = 100
        for i in range(0, len(rows), BATCH):
            batch = rows[i : i + BATCH]
            conn.executemany(
                """INSERT INTO volume_snapshots
                   (type_id, region_id, date, buy_price, sell_price,
                    buy_volume, sell_volume, order_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                [(r[0], r[1], r[2], r[3], r[3], r[6], r[6], r[7]) for r in batch],
            )
        total += len(rows)

    conn.commit()
    logger.info("历史量价拉取完成: %d 条", total)


def run_history_update(targets: list[tuple[int, int]] | None = None):
    """同步入口"""
    asyncio.run(fetch_history(targets))
