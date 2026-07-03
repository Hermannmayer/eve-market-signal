"""
从 SDE ZIP 构建 reference.db（物品名称 + 市场分组）

数据源: https://eve-static-data-export.s3-eu-west-1.amazonaws.com/tranquility/sde.zip

首次运行自动下载缓存，后续跳过。
"""

import io
import logging
import os
import zipfile

import aiohttp
import yaml

from eve_reuse.paths import data_dir
from signals.db import get_ref_db

logger = logging.getLogger(__name__)

SDE_URL = (
    "https://eve-static-data-export.s3-eu-west-1.amazonaws.com/tranquility/sde.zip"
)


def _sde_zip_path() -> str:
    return os.path.join(data_dir(), "sde.zip")


def _yaml_cache_path(name: str) -> str:
    return os.path.join(data_dir(), name)


def is_reference_built() -> bool:
    """检查 reference.db 是否已有数据"""
    conn = get_ref_db()
    row = conn.execute("SELECT COUNT(*) AS cnt FROM item").fetchone()
    return row["cnt"] >= 50000


# ── SDE 下载 ──────────────────────────────────────────


async def download_sde(force: bool = False) -> str:
    """下载 SDE ZIP（首次），返回本地路径"""
    dest = _sde_zip_path()
    if os.path.exists(dest) and not force:
        logger.info("SDE ZIP 已存在: %s", dest)
        return dest

    logger.info("下载 SDE 数据 (112MB)…")
    async with aiohttp.ClientSession() as session:
        async with session.get(SDE_URL) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as f:
                async for chunk in resp.content.iter_chunked(8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded * 100 // total
                        logger.info("SDE 下载: %d/%d MB (%d%%)", downloaded // 1048576, total // 1048576, pct)
    logger.info("SDE 下载完成: %s", dest)
    return dest


# ── YAML 提取 ──────────────────────────────────────────


def _extract_yaml(zip_path: str, yaml_name: str) -> dict:
    """从 ZIP 中提取单个 YAML 文件并解析"""
    cache_path = _yaml_cache_path(yaml_name)
    if os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    logger.info("提取 %s…", yaml_name)
    with zipfile.ZipFile(zip_path, "r") as zf:
        # SDE ZIP 内路径如 sde/typeIDs.yaml
        for member in zf.namelist():
            if member.endswith(yaml_name):
                raw = zf.read(member)
                # 保存缓存
                with open(cache_path, "wb") as f:
                    f.write(raw)
                return yaml.safe_load(io.BytesIO(raw).read())
    raise FileNotFoundError(f"{yaml_name} not found in SDE ZIP")


# ── 构建参考库 ──────────────────────────────────────────


def _build_item_table(type_ids: dict, group_ids: dict):
    """写入 item 表"""
    conn = get_ref_db()
    conn.execute("DELETE FROM item")

    rows = []
    for tid, data in type_ids.items():
        if not isinstance(data, dict):
            continue
        en_name = data.get("name", {}).get("en", "") if isinstance(data.get("name"), dict) else ""
        zh_name = data.get("name", {}).get("zh", "") if isinstance(data.get("name"), dict) else ""
        group_id = data.get("groupID", 0)
        volume = data.get("volume", 0)
        icon_id = data.get("iconID", 0)
        market_group_id = data.get("marketGroupID")

        # group 名
        en_group = ""
        zh_group = ""
        if group_id and group_id in group_ids:
            g = group_ids[group_id]
            en_group = g.get("name", {}).get("en", "") if isinstance(g.get("name"), dict) else ""
            zh_group = g.get("name", {}).get("zh", "") if isinstance(g.get("name"), dict) else ""

        rows.append((
            int(tid), en_name, zh_name,
            group_id, en_group, zh_group,
            market_group_id,
            en_name[:200] if en_name else "",
            zh_name[:200] if zh_name else "",
            volume, icon_id,
        ))

    BATCH = 500
    for i in range(0, len(rows), BATCH):
        batch = rows[i : i + BATCH]
        conn.executemany(
            """INSERT OR REPLACE INTO item
               (type_id, en_name, zh_name, group_id, en_group_name, zh_group_name,
                market_group_id, en_market_group_name, zh_market_group_name, volume, iconID)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            batch,
        )
    conn.commit()
    logger.info("写入 item 表: %d 条", len(rows))


def _build_market_tree(market_groups: dict):
    """写入 market_tree 表"""
    conn = get_ref_db()
    conn.execute("DELETE FROM market_tree")

    rows = []
    for mgid, data in market_groups.items():
        if not isinstance(data, dict):
            continue
        en_name = data.get("name", {}).get("en", "") if isinstance(data.get("name"), dict) else ""
        zh_name = data.get("name", {}).get("zh", "") if isinstance(data.get("name"), dict) else ""
        parent = data.get("parentGroupID")
        icon_id = data.get("iconID", 0)
        rows.append((int(mgid), parent, en_name, zh_name, icon_id))

    conn.executemany(
        "INSERT OR REPLACE INTO market_tree (market_group_id, parent_group_id, en_name, zh_name, icon_id) VALUES (?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    logger.info("写入 market_tree 表: %d 条", len(rows))


async def build_reference(force: bool = False):
    """主入口：构建 reference.db"""
    if is_reference_built() and not force:
        logger.info("reference.db 已有数据，跳过构建")
        return

    os.makedirs(data_dir(), exist_ok=True)

    # 下载 SDE
    zip_path = await download_sde(force)

    # 解析 YAML
    type_ids = _extract_yaml(zip_path, "typeIDs.yaml")
    group_ids = _extract_yaml(zip_path, "groupIDs.yaml")
    market_groups = _extract_yaml(zip_path, "marketGroups.yaml")

    # 写入数据库
    _build_item_table(type_ids, group_ids)
    _build_market_tree(market_groups)

    logger.info("reference.db 构建完成")


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(build_reference())
