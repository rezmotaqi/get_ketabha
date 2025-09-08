#!/usr/bin/env python3
"""
Simple LibGen search - returns only: title, author, format, year
"""
import asyncio
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from libgen_search import LibGenSearcher

async def simple_search(query):
    """Search and return only essential book information"""
    searcher = LibGenSearcher()
    
    print(f"Searching for: {query}\n")
    results = await searcher.search(query)
    
    if not results:
        print("No results found")
        return
        
    for i, book in enumerate(results, 1):
        title = book.get('title', 'Unknown Title')
        author = book.get('author', 'Unknown Author')
        year = book.get('year', 'Unknown')
        format_ext = book.get('extension', 'Unknown').upper()
        
        print(f"{i}. {title}")
        print(f"   Author: {author}")
        print(f"   Format: {format_ext} | Year: {year}")
        print()

if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "Python programming"
    asyncio.run(simple_search(query))
