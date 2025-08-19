import httpx
from typing import Dict
from loguru import logger

from src.config.env import CRAWL_URL

async def crawl_markdown(url: str) -> Dict:
    """Crawl URL using external Crawl4AI service"""
    logger.info(f"Crawling URL: {url}")
    
    # Official Crawl4AI Docker API format
    browser_config_payload = {
        "type": "BrowserConfig",
        "params": {"headless": True}
    }
    
    crawler_config_payload = {
        "type": "CrawlerRunConfig", 
        "params": {
            "stream": False,
            "cache_mode": "bypass",
            "word_count_threshold": 100,
            "only_text": False,
            "skip_internal_links": True,
            "extraction_strategy": {
                "type": "BM25ExtractionStrategy",
                "params": {
                    "top_k": 10,
                    "word_count_threshold": 100
                }
            }
        }
    }
    
    payload = {
        "urls": [url],
        "browser_config": browser_config_payload,
        "crawler_config": crawler_config_payload
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.debug(f"Making crawl request with payload: {payload}")
            
            r = await client.post(CRAWL_URL, json=payload)
            logger.info(f"Crawl response status for {url}: {r.status_code}")
            
            r.raise_for_status()
            response_data = r.json()
            
            # Crawl4AI Docker returns a container with results array
            if "results" in response_data and len(response_data["results"]) > 0:
                result = response_data["results"][0]  # Get first result
            else:
                result = response_data
            
            # Extract content from the crawl result
            markdown_content = result.get("markdown", "")
            success = result.get("success", False)
            
            # If main markdown is empty, try alternative fields
            if not markdown_content or len(markdown_content.strip()) < 50:
                markdown_content = result.get("cleaned_html", "")
                if not markdown_content:
                    markdown_content = result.get("extracted_content", "")
            
            if isinstance(markdown_content, str) and len(markdown_content.strip()) > 50:
                logger.info(f"Successfully crawled {url}: {len(markdown_content)} chars of markdown")
            else:
                logger.warning(f"Poor markdown extraction for {url}: '{markdown_content}' (type: {type(markdown_content)})")
                
                # Log debugging info
                success = result.get("success", False)
                error_msg = result.get("error_message", "")
                status_code = result.get("status_code", 0)
                
                logger.warning(f"Crawl details - Success: {success}, Status: {status_code}, Error: {error_msg}")
                markdown_content = ""
            
            return {
                "url": url,
                "markdown": markdown_content,
                "success": result.get("success", True),
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
