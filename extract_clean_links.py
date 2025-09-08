#!/usr/bin/env python3
"""
Extract clean book data from LibGen search results
"""
import asyncio
import sys
import os
import html

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from libgen_search import LibGenSearcher

async def search_and_extract(query):
    """Search and extract clean book data"""
    searcher = LibGenSearcher()
    
    print(f"🔍 Searching for: {query}")
    results = await searcher.search(query)
    
    if not results:
        print("❌ No results found")
        return
        
    print(f"\n📚 Found {len(results)} books:\n")
    
    for i, book in enumerate(results, 1):
        title = book.get('title', 'Unknown Title')
        author = book.get('author', 'Unknown Author')
        year = book.get('year', '')
        size = book.get('size', '')
        ext = book.get('extension', '')
        md5 = book.get('md5', '')
        
        # Clean up any HTML entities
        title = html.unescape(title)
        author = html.unescape(author)
        
        print(f"{i}. {title}")
        print(f"   Author: {author}")
        if year:
            print(f"   Year: {year} | Size: {size} | Format: {ext}")
        if md5:
            print(f"   MD5: {md5}")
            
        # Get download links
        if md5:
            try:
                download_links = await searcher.get_download_links(md5)
                if download_links:
                    print(f"   📥 Download Links:")
                    for j, link in enumerate(download_links[:3], 1):
                        link_name = link.get('name') or link.get('text') or f'Download {j}'
                        link_url = link.get('url', '')
                        print(f"      {j}. {link_url}")
                else:
                    print(f"   📥 No direct download links found")
            except Exception as e:
                print(f"   📥 Error getting download links: {e}")
        print()

if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "Clean Code Robert Martin"
    asyncio.run(search_and_extract(query))
