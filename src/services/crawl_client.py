import httpx, os, asyncio
from typing import Dict

from src.config.env import CRAWL_URL

async def crawl_markdown(url: str) -> Dict:
    payload = {
        "url": url,
        "f": "bm25",
        "q": None,
        "c": "0"
    }
    async with httpx.AsyncClient(timeout=60) as cli:
        r = await cli.post(CRAWL_URL, json=payload)
    r.raise_for_status()
    return r.json()
