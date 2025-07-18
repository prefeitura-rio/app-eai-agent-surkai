import httpx
from typing import List, Dict

from src.config.env import SEARX_URL

async def searx_search(query: str, k: int = 6, lang: str = "pt-BR") -> List[Dict]:
    params = {
        "q": query,
        "format": "json",
        "language": lang,
        "safesearch": 1,
        "categories": "general",
    }
    async with httpx.AsyncClient(timeout=20) as cli:
        r = await cli.get(SEARX_URL, params=params)
    r.raise_for_status()
    data = r.json()
    results = data.get("results", [])
    results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)
    return results[:k]
