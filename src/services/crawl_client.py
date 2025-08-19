import httpx
from typing import Dict
import asyncio
from loguru import logger

from src.config.env import CRAWL_URL

# Reusable HTTP client with connection pooling
_http_client = None

async def get_http_client():
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=5.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
        )
    return _http_client

async def crawl_markdown(url: str) -> Dict:
    logger.info(f"Crawling URL: {url}")
    logger.debug(f"Crawl4AI URL: {CRAWL_URL}")
    
    payload = {
        "urls": [url],
        "f": "bm25",
        "skip_internal_links": True,
        "c": "0"
    }
    
    try:
        cli = await get_http_client()
        logger.debug(f"Making crawl request with payload: {payload}")
        r = await cli.post(CRAWL_URL, json=payload)
        logger.info(f"Crawl response status for {url}: {r.status_code}")
            
        r.raise_for_status()
        result = r.json()
        
        if isinstance(result, list) and len(result) > 0:
            result = result[0]
        elif isinstance(result, dict) and "results" in result and len(result["results"]) > 0:
            result = result["results"][0]
        
        markdown_content = result.get("markdown", "")
        content_content = result.get("content", "")
        content_length = len(markdown_content) if markdown_content else len(content_content)
        
        logger.info(f"Crawled {url}: {content_length} chars of content")
        logger.debug(f"Response keys: {list(result.keys())}")
        
        return result
        
    except httpx.TimeoutException as e:
        logger.error(f"Timeout crawling {url}: {e}")
        raise
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error crawling {url}: {e.response.status_code} - {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error crawling {url}: {e}")
        raise
