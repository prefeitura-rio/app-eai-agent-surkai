#!/usr/bin/env python3
"""Test script to verify Crawl4AI connectivity and API format"""

import asyncio
import httpx
import json
from datetime import datetime

async def test_crawl4ai():
    """Test Crawl4AI service connectivity"""
    
    # Test URL
    test_url = "https://httpbin.org/json"
    
    # Crawl4AI endpoint
    crawl_url = "http://crawl4ai/crawl"  # Internal k8s service
    
    # Official API format based on Crawl4AI Docker docs
    payload = {
        "urls": [test_url],
        "browser_config": {
            "type": "BrowserConfig",
            "params": {"headless": True}
        },
        "crawler_config": {
            "type": "CrawlerRunConfig", 
            "params": {
                "stream": False,
                "cache_mode": "bypass",
                "word_count_threshold": 10,
                "only_text": False,
                "skip_internal_links": True,
                "extraction_strategy": {
                    "type": "BM25ExtractionStrategy",
                    "params": {
                        "top_k": 3,
                        "word_count_threshold": 10
                    }
                }
            }
        }
    }
    
    print(f"[{datetime.now()}] Testing Crawl4AI connectivity...")
    print(f"URL: {crawl_url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print(f"[{datetime.now()}] Making request...")
            
            response = await client.post(crawl_url, json=payload)
            
            print(f"[{datetime.now()}] Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response data keys: {list(data.keys())}")
                
                if "results" in data:
                    results = data["results"]
                    print(f"Number of results: {len(results)}")
                    if results:
                        result = results[0]
                        print(f"First result keys: {list(result.keys())}")
                        print(f"Success: {result.get('success')}")
                        print(f"Markdown length: {len(result.get('markdown', ''))}")
                else:
                    print("No 'results' key in response")
                    print(f"Response: {json.dumps(data, indent=2)[:500]}...")
            else:
                print(f"Error response: {response.text}")
                
    except httpx.TimeoutException as e:
        print(f"[{datetime.now()}] TIMEOUT ERROR: {e}")
    except httpx.ConnectError as e:
        print(f"[{datetime.now()}] CONNECTION ERROR: {e}")
    except Exception as e:
        print(f"[{datetime.now()}] UNEXPECTED ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_crawl4ai())