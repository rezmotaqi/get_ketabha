#!/usr/bin/env python3
"""
LibGen Service - Integrates with existing LibGen search functionality
"""

import sys
import os
import asyncio
from typing import List, Dict, Any
from datetime import datetime

# Add the parent directory to Python path to import existing bot modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.libgen_search import LibGenSearcher
from schemas import BookInfo, DownloadLink

class LibGenService:
    """Service class for LibGen operations in the dashboard"""
    
    def __init__(self):
        """Initialize the LibGen service"""
        self.searcher = LibGenSearcher()
        
    async def search_books(self, query: str, max_results: int = 50) -> List[BookInfo]:
        """
        Search for books using the existing LibGen searcher
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List of BookInfo objects
        """
        try:
            # Use the existing searcher
            raw_results = await self.searcher.search(query, max_results)
            
            # Convert to our schema format
            books = []
            for book_data in raw_results:
                book = BookInfo(
                    title=book_data.get('title', 'Unknown Title'),
                    author=book_data.get('author', 'Unknown Author'),
                    year=book_data.get('year', ''),
                    pages=book_data.get('pages', ''),
                    language=book_data.get('language', ''),
                    size=book_data.get('size', ''),
                    extension=book_data.get('extension', ''),
                    md5=book_data.get('md5', ''),
                    publisher=book_data.get('publisher', ''),
                    isbn=book_data.get('identifier', ''),
                    description=book_data.get('description', ''),
                    cover_url=book_data.get('cover_url', '')
                )
                books.append(book)
            
            return books
            
        except Exception as e:
            print(f"Error searching books: {str(e)}")
            raise e
    
    async def get_download_links(self, md5_hash: str) -> List[DownloadLink]:
        """
        Get download links for a specific book
        
        Args:
            md5_hash: MD5 hash of the book
            
        Returns:
            List of DownloadLink objects
        """
        try:
            # Use the existing searcher to get download links
            raw_links = await self.searcher.get_download_links(md5_hash)
            
            # Convert to our schema format
            links = []
            for link_data in raw_links:
                link = DownloadLink(
                    url=link_data.get('url', ''),
                    type=link_data.get('type', 'direct'),
                    mirror=link_data.get('mirror', ''),
                    quality=link_data.get('quality', 'standard')
                )
                links.append(link)
            
            return links
            
        except Exception as e:
            print(f"Error getting download links: {str(e)}")
            raise e
    
    def get_available_mirrors(self) -> List[str]:
        """Get list of available LibGen mirrors"""
        return self.searcher.libgen_mirrors
    
    async def test_mirror_connectivity(self) -> Dict[str, bool]:
        """Test connectivity to all mirrors"""
        results = {}
        for mirror in self.searcher.libgen_mirrors:
            try:
                # Simple connectivity test
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(mirror, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        results[mirror] = response.status == 200
            except Exception:
                results[mirror] = False
        
        return results
    
    async def get_popular_books(self, limit: int = 10) -> List[BookInfo]:
        """
        Get popular books (simulation - in real implementation, 
        this would query a database of popular searches)
        """
        popular_queries = [
            "python programming",
            "machine learning", 
            "data science",
            "javascript",
            "algorithms",
            "deep learning",
            "web development",
            "artificial intelligence",
            "computer science",
            "software engineering"
        ]
        
        all_books = []
        for query in popular_queries[:3]:  # Limit to avoid too many requests
            try:
                books = await self.search_books(query, max_results=5)
                all_books.extend(books[:2])  # Take top 2 from each query
            except Exception:
                continue
        
        return all_books[:limit]
    
    async def get_book_details(self, md5_hash: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific book
        """
        try:
            # For now, we'll search by MD5 to get book details
            # In a real implementation, you might have a dedicated method
            links = await self.get_download_links(md5_hash)
            
            return {
                "md5": md5_hash,
                "download_links": [link.dict() for link in links],
                "details_fetched_at": datetime.utcnow().isoformat(),
                "available_formats": list(set([link.type for link in links])),
                "mirror_count": len(set([link.mirror for link in links if link.mirror]))
            }
            
        except Exception as e:
            print(f"Error getting book details: {str(e)}")
            raise e
    
    def get_search_suggestions(self, partial_query: str) -> List[str]:
        """
        Get search suggestions based on partial query
        """
        # Simple implementation - in production, you'd use a more sophisticated approach
        suggestions = [
            "python programming",
            "machine learning",
            "data science", 
            "javascript tutorial",
            "algorithms and data structures",
            "web development",
            "artificial intelligence",
            "deep learning",
            "computer networks",
            "database systems",
            "software engineering",
            "operating systems",
            "computer graphics",
            "cybersecurity",
            "mobile app development"
        ]
        
        # Filter suggestions based on partial query
        if partial_query:
            filtered = [s for s in suggestions if partial_query.lower() in s.lower()]
            return filtered[:5]
        
        return suggestions[:5]
