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
    
    # First, test if the service is reachable
    try:
        cli = await get_http_client()
        health_check = await cli.get(CRAWL_URL.replace('/crawl', '/health'), timeout=5.0)
        logger.debug(f"Crawl4AI health check: {health_check.status_code}")
    except Exception as e:
        logger.warning(f"Crawl4AI health check failed: {e}")
    
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
        
        # Use only markdown content as intended
        markdown_content = result.get("markdown", "")
        
        if isinstance(markdown_content, str) and len(markdown_content.strip()) > 50:
            logger.info(f"Crawled {url}: {len(markdown_content)} chars of markdown")
        else:
            # Log what we got to debug the issue
            logger.warning(f"Poor markdown extraction for {url}: '{markdown_content}' (type: {type(markdown_content)})")
            
            # Check if crawling actually succeeded
            success = result.get("success", False)
            error_msg = result.get("error_message", "")
            status_code = result.get("status_code", 0)
            
            logger.warning(f"Crawl details - Success: {success}, Status: {status_code}, Error: {error_msg}")
            
            # Set empty markdown if unusable
            result["markdown"] = ""
            
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
