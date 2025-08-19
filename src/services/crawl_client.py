import httpx
from typing import Dict
from loguru import logger

from src.config.env import CRAWL_URL

async def crawl_markdown(url: str) -> Dict:
    logger.info(f"Crawling URL: {url}")
    logger.debug(f"Crawl4AI URL: {CRAWL_URL}")
    
    payload = {
        "url": url,
        "f": "bm25",
        "skip_internal_links": True,
        "c": "0"
    }
    
    try:
        async with httpx.AsyncClient(timeout=60) as cli:
            logger.debug(f"Making crawl request with payload: {payload}")
            r = await cli.post(CRAWL_URL, json=payload)
            logger.info(f"Crawl response status for {url}: {r.status_code}")
            
        r.raise_for_status()
        result = r.json()
        
        # Log some info about the response
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
