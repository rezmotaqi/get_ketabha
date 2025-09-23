#!/usr/bin/env python3
"""
Mirror Status Checker
Checks the availability and response time of LibGen mirrors.
"""

import asyncio
import aiohttp
import time
from typing import List, Dict, Any
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.libgen_search import LibGenSearcher

async def check_mirror_status(url: str, timeout: int = 10) -> Dict[str, Any]:
    """Check if a mirror is accessible and measure response time."""
    start_time = time.time()
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            # Try to access the main page
            async with session.get(url) as response:
                response_time = time.time() - start_time
                
                if response.status == 200:
                    return {
                        'url': url,
                        'status': '✅ ONLINE',
                        'response_time': f"{response_time:.2f}s",
                        'http_status': response.status,
                        'accessible': True
                    }
                else:
                    return {
                        'url': url,
                        'status': f'⚠️ HTTP {response.status}',
                        'response_time': f"{response_time:.2f}s",
                        'http_status': response.status,
                        'accessible': False
                    }
                    
    except asyncio.TimeoutError:
        return {
            'url': url,
            'status': '❌ TIMEOUT',
            'response_time': f">{timeout}s",
            'http_status': None,
            'accessible': False
        }
    except Exception as e:
        response_time = time.time() - start_time
        return {
            'url': url,
            'status': f'❌ ERROR: {str(e)[:30]}...',
            'response_time': f"{response_time:.2f}s",
            'http_status': None,
            'accessible': False
        }

async def check_all_mirrors():
    """Check all configured mirrors."""
    print("🔍 **LibGen Mirror Status Check**\n")
    
    # Initialize searcher to get mirror list
    searcher = LibGenSearcher()
    
    print(f"📊 **Search Mirrors ({len(searcher.libgen_mirrors)}):**\n")
    
    # Check search mirrors
    search_tasks = [check_mirror_status(url) for url in searcher.libgen_mirrors]
    search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
    
    for i, result in enumerate(search_results, 1):
        if isinstance(result, Exception):
            print(f"{i:2d}. ❌ ERROR: {result}")
        else:
            print(f"{i:2d}. {result['status']} {result['url']} ({result['response_time']})")
    
    print(f"\n📥 **Download Mirrors ({len(searcher.download_mirrors)}):**\n")
    
    # Check download mirrors
    download_tasks = [check_mirror_status(url) for url in searcher.download_mirrors]
    download_results = await asyncio.gather(*download_tasks, return_exceptions=True)
    
    for i, result in enumerate(download_results, 1):
        if isinstance(result, Exception):
            print(f"{i:2d}. ❌ ERROR: {result}")
        else:
            print(f"{i:2d}. {result['status']} {result['url']} ({result['response_time']})")
    
    # Summary
    online_search = sum(1 for r in search_results if not isinstance(r, Exception) and r['accessible'])
    online_download = sum(1 for r in download_results if not isinstance(r, Exception) and r['accessible'])
    
    print(f"\n📈 **Summary:**")
    print(f"   Search Mirrors: {online_search}/{len(searcher.libgen_mirrors)} online")
    print(f"   Download Mirrors: {online_download}/{len(searcher.download_mirrors)} online")
    
    if online_search == 0:
        print("\n⚠️ **WARNING:** No search mirrors are accessible!")
    if online_download == 0:
        print("\n⚠️ **WARNING:** No download mirrors are accessible!")

if __name__ == "__main__":
    asyncio.run(check_all_mirrors())

