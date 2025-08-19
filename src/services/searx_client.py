import httpx
from typing import List, Dict
from loguru import logger

from src.config.env import SEARX_URL

async def searx_search(query: str, k: int = 6, lang: str = "pt-BR") -> List[Dict]:
    logger.info(f"Searching SearX for query: '{query}', k={k}, lang={lang}")
    logger.info(f"SearX URL: {SEARX_URL}")
    
    params = {
        "q": query,
        "format": "json",
        "language": lang,
        "safesearch": 1,
        "categories": "general",
    }
    
    try:
        async with httpx.AsyncClient(timeout=20) as cli:
            logger.debug(f"Making request to SearX with params: {params}")
            r = await cli.get(SEARX_URL, params=params)
            logger.info(f"SearX response status: {r.status_code}")
            
        r.raise_for_status()
        data = r.json()
        results = data.get("results", [])
        logger.info(f"SearX returned {len(results)} raw results")
        
        results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)
        final_results = results[:k]
        logger.info(f"Returning top {len(final_results)} results")
        
        for i, result in enumerate(final_results):
            logger.debug(f"Result {i+1}: {result.get('title', 'No title')} - {result.get('url', 'No URL')}")
            
        return final_results
        
    except httpx.TimeoutException as e:
        logger.error(f"Timeout connecting to SearX: {e}")
        raise
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from SearX: {e.response.status_code} - {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in SearX search: {e}")
        raise
