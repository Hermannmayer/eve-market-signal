"""
共享 ESI HTTP 客户端 — 限流、重试、并发控制

用法:
    client = ESIClient()
    data = await client.fetch("/markets/prices/")
"""

import asyncio
import logging

import aiohttp

logger = logging.getLogger(__name__)

BASE_URL = "https://esi.evetech.net/latest"
USER_AGENT = "EVEMarketSignal/1.0"


class ESIClient:
    """ESI API 客户端，提供限流和重试"""

    def __init__(
        self,
        concurrency: int = 20,
        timeout: int = 30,
        user_agent: str = USER_AGENT,
        retries: int = 3,
    ):
        self._semaphore = asyncio.Semaphore(concurrency)
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._headers = {"Accept": "application/json", "User-Agent": user_agent}
        self._retries = retries

    async def fetch(self, path: str) -> dict | list | None:
        """GET 请求，404/超时返回 None"""
        url = f"{BASE_URL}/{path.lstrip('/')}"
        for attempt in range(1, self._retries + 1):
            try:
                async with self._semaphore:
                    async with aiohttp.ClientSession(
                        headers=self._headers, timeout=self._timeout
                    ) as session:
                        async with session.get(url) as resp:
                            if resp.status == 404:
                                return None
                            if resp.status == 429:
                                await self._handle_rate_limit(resp)
                                continue
                            if resp.status >= 500:
                                if attempt < self._retries:
                                    wait = 2**attempt
                                    logger.warning(
                                        "ESI %d on %s, retry %d/%d in %ds",
                                        resp.status, url, attempt, self._retries, wait,
                                    )
                                    await asyncio.sleep(wait)
                                    continue
                                resp.raise_for_status()
                            resp.raise_for_status()
                            return await resp.json()
            except (TimeoutError, aiohttp.ClientError) as exc:
                if attempt < self._retries:
                    wait = 2**attempt
                    logger.warning(
                        "ESI error on %s: %s, retry %d/%d in %ds",
                        url, exc, attempt, self._retries, wait,
                    )
                    await asyncio.sleep(wait)
                    continue
                logger.exception("ESI failed after %d retries: %s", self._retries, url)
                return None
        return None

    async def fetch_required(self, path: str) -> dict | list:
        """GET 请求，失败抛出异常"""
        result = await self.fetch(path)
        if result is None:
            raise RuntimeError(f"ESI fetch failed (required): {path}")
        return result

    async def get_text(self, path: str) -> str | None:
        """GET 请求返回原始文本"""
        url = f"{BASE_URL}/{path.lstrip('/')}"
        try:
            async with self._semaphore:
                async with aiohttp.ClientSession(
                    headers=self._headers, timeout=self._timeout
                ) as session:
                    async with session.get(url) as resp:
                        if resp.status == 404:
                            return None
                        resp.raise_for_status()
                        return await resp.text()
        except (TimeoutError, aiohttp.ClientError):
            logger.exception("ESI get_text failed: %s", url)
            return None

    @staticmethod
    async def _handle_rate_limit(resp: aiohttp.ClientResponse) -> None:
        """处理 429 限流"""
        retry_after = resp.headers.get("Retry-After", "30")
        wait_time = int(retry_after) if retry_after.isdigit() else 30
        await asyncio.sleep(min(wait_time, 120))
