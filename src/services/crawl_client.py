import httpx
from typing import Dict
from loguru import logger

from src.config.env import CRAWL_URL

async def crawl_markdown(url: str) -> Dict:
    """Crawl URL using external Crawl4AI service"""
    logger.info(f"Crawling URL: {url}")
    logger.debug(f"Crawl4AI URL: {CRAWL_URL}")
    
    # Simple API format based on actual logs
    payload = {
        "urls": [url],
        "f": "bm25",  # BM25 extraction strategy
        "skip_internal_links": True,
        "c": "0"  # Cache bypass
    }
    
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=5.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
        ) as client:
            logger.debug(f"Making crawl request with payload: {payload}")
            
            r = await client.post(CRAWL_URL, json=payload)
            logger.info(f"Crawl response status for {url}: {r.status_code}")
            
            r.raise_for_status()
            response_data = r.json()
            logger.debug(f"Response keys: {list(response_data.keys())}")
            
            # Extract content - try different possible response formats
            markdown_content = ""
            result = response_data
            
            # If it has results array, use first result
            if "results" in response_data and len(response_data["results"]) > 0:
                result = response_data["results"][0]
            
            # Try to get markdown content
            markdown_content = result.get("markdown", "")
            
            # If main markdown is empty or too short, try alternatives
            if not markdown_content or len(str(markdown_content).strip()) < 50:
                markdown_content = result.get("cleaned_html", "")
                if not markdown_content or len(str(markdown_content).strip()) < 50:
                    markdown_content = result.get("extracted_content", "")
                    if not markdown_content or len(str(markdown_content).strip()) < 50:
                        markdown_content = result.get("content", "")
            
            # Ensure content is string
            if not isinstance(markdown_content, str):
                markdown_content = str(markdown_content) if markdown_content else ""
            
            content_length = len(markdown_content.strip())
            logger.info(f"Crawled {url}: {content_length} chars of content")
            
            if content_length < 50:
                logger.warning(f"Content too short for {url}, response: {response_data}")
                markdown_content = ""
            
            return {
                "url": url,
                "markdown": markdown_content,
                "content": markdown_content,  # Alias for backward compatibility
                "success": result.get("success", content_length > 0),
                "status_code": result.get("status_code", 200),
                "error_message": result.get("error_message", "")
            }
        
    except httpx.TimeoutException as e:
        logger.error(f"Timeout crawling {url}: {e}")
        return {
            "url": url,
            "markdown": "",
            "success": False,
            "status_code": 0,
            "error_message": f"Timeout after 30s: {str(e)}"
        }
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error crawling {url}: {e.response.status_code} - {e.response.text}")
        return {
            "url": url,
            "markdown": "",
            "success": False,
            "status_code": e.response.status_code,
            "error_message": f"HTTP {e.response.status_code}: {e.response.text}"
        }
    except Exception as e:
        logger.error(f"Unexpected error crawling {url}: {e}")
        return {
            "url": url,
            "markdown": "",
            "success": False,
            "status_code": 0,
            "error_message": str(e)
        }
