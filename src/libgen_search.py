#!/usr/bin/env python3
"""
LibGen Search Module
Handles searching LibGen sites and extracting book information and download links.
"""

import asyncio
import aiohttp
import re
from typing import List, Dict, Any, Optional
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup
import logging

from utils.logger import setup_logger

logger = setup_logger(__name__)

class LibGenSearcher:
    """Main class for searching LibGen sites."""
    
    # LibGen mirror URLs
    LIBGEN_MIRRORS = [
        "http://libgen.rs",
        "http://libgen.is",
        "http://libgen.st",
        "https://libgen.fun",
    ]
    
    # Download mirrors
    DOWNLOAD_MIRRORS = [
        "http://library.lol",
        "http://libgen.rs",
        "http://libgen.is",
    ]
    
    def __init__(self, timeout: int = 30, max_retries: int = 3):
        """Initialize the searcher."""
        self.timeout = timeout
        self.max_retries = max_retries
        
    async def search(self, query: str, max_results: int = 25) -> List[Dict[str, Any]]:
        """
        Search for books across LibGen mirrors.
        
        Args:
            query: Search query (title, author, ISBN, etc.)
            max_results: Maximum number of results to return
            
        Returns:
            List of book dictionaries with metadata
        """
        logger.info(f"Searching for: {query}")
        
        results = []
        
        # Try each mirror until we get results
        for mirror in self.LIBGEN_MIRRORS:
            try:
                mirror_results = await self._search_mirror(mirror, query, max_results)
                if mirror_results:
                    results.extend(mirror_results)
                    logger.info(f"Found {len(mirror_results)} results from {mirror}")
                    break
                    
            except Exception as e:
                logger.warning(f"Failed to search {mirror}: {str(e)}")
                continue
                
        # Remove duplicates based on MD5 hash
        unique_results = self._remove_duplicates(results)
        
        logger.info(f"Total unique results: {len(unique_results)}")
        return unique_results[:max_results]
        
    async def _search_mirror(self, mirror: str, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search a specific LibGen mirror."""
        search_url = f"{mirror}/search.php"
        params = {
            'req': query,
            'lg_topic': 'libgen',
            'open': '0',
            'view': 'simple',
            'res': str(min(max_results, 100)),  # Max 100 per request
            'phrase': '1',
            'column': 'def'
        }
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
            for attempt in range(self.max_retries):
                try:
                    async with session.get(search_url, params=params) as response:
                        if response.status == 200:
                            html = await response.text()
                            return self._parse_search_results(html, mirror)
                        else:
                            logger.warning(f"HTTP {response.status} from {mirror}")
                            
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout on attempt {attempt + 1} for {mirror}")
                except Exception as e:
                    logger.warning(f"Request error on attempt {attempt + 1} for {mirror}: {str(e)}")
                    
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1)  # Brief delay before retry
                    
        return []
        
    def _parse_search_results(self, html: str, base_url: str) -> List[Dict[str, Any]]:
        """Parse HTML search results into structured data."""
        results = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find results table
            table = soup.find('table', {'rules': 'cols'})
            if not table:
                return results
                
            rows = table.find_all('tr')[1:]  # Skip header row
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 10:  # Ensure we have enough columns
                    continue
                    
                try:
                    # Extract book information
                    book_info = {
                        'id': cells[0].get_text(strip=True),
                        'author': cells[1].get_text(strip=True),
                        'title': cells[2].get_text(strip=True),
                        'publisher': cells[3].get_text(strip=True),
                        'year': cells[4].get_text(strip=True),
                        'pages': cells[5].get_text(strip=True),
                        'language': cells[6].get_text(strip=True),
                        'size': cells[7].get_text(strip=True),
                        'extension': cells[8].get_text(strip=True),
                        'mirrors': []
                    }
                    
                    # Extract MD5 hash and download links from the mirrors column
                    mirrors_cell = cells[9]
                    links = mirrors_cell.find_all('a')
                    
                    for link in links:
                        href = link.get('href', '')
                        if 'md5=' in href:
                            # Extract MD5 hash
                            md5_match = re.search(r'md5=([a-f0-9]{32})', href)
                            if md5_match:
                                book_info['md5'] = md5_match.group(1)
                                book_info['mirrors'].append({
                                    'url': urljoin(base_url, href),
                                    'type': 'details'
                                })
                    
                    # Clean up data
                    book_info = self._clean_book_info(book_info)
                    
                    if book_info['title'] and book_info['author']:  # Must have title and author
                        results.append(book_info)
                        
                except Exception as e:
                    logger.warning(f"Error parsing result row: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error parsing search results: {str(e)}")
            
        return results
        
    def _clean_book_info(self, book_info: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and normalize book information."""
        # Clean title
        title = book_info.get('title', '').strip()
        # Remove common prefixes/suffixes that clutter results
        title = re.sub(r'^(A |An |The )', '', title, flags=re.IGNORECASE)
        book_info['title'] = title
        
        # Clean author
        author = book_info.get('author', '').strip()
        book_info['author'] = author
        
        # Normalize year
        year = book_info.get('year', '').strip()
        year_match = re.search(r'\b(19|20)\d{2}\b', year)
        book_info['year'] = year_match.group(0) if year_match else year
        
        # Clean size
        size = book_info.get('size', '').strip()
        book_info['size'] = size if size and size != '0' else 'Unknown'
        
        # Clean extension
        ext = book_info.get('extension', '').strip().lower()
        book_info['extension'] = ext
        
        # Clean pages
        pages = book_info.get('pages', '').strip()
        book_info['pages'] = pages if pages and pages != '0' else 'Unknown'
        
        return book_info
        
    async def get_download_links(self, md5_hash: str) -> List[Dict[str, str]]:
        """
        Get direct download links for a book using its MD5 hash.
        
        Args:
            md5_hash: MD5 hash of the book
            
        Returns:
            List of download link dictionaries
        """
        download_links = []
        
        for mirror in self.DOWNLOAD_MIRRORS:
            try:
                links = await self._get_download_links_from_mirror(mirror, md5_hash)
                download_links.extend(links)
            except Exception as e:
                logger.warning(f"Failed to get download links from {mirror}: {str(e)}")
                continue
                
        return download_links
        
    async def _get_download_links_from_mirror(self, mirror: str, md5_hash: str) -> List[Dict[str, str]]:
        """Get download links from a specific mirror."""
        download_urls = []
        
        # Try different URL patterns for the mirror
        url_patterns = [
            f"{mirror}/main/{md5_hash}",
            f"{mirror}/book/index.php?md5={md5_hash}",
        ]
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
            for url in url_patterns:
                try:
                    async with session.get(url) as response:
                        if response.status == 200:
                            html = await response.text()
                            links = self._extract_download_links(html, mirror)
                            if links:
                                download_urls.extend(links)
                                break
                except Exception as e:
                    logger.warning(f"Error fetching {url}: {str(e)}")
                    continue
                    
        return download_urls
        
    def _extract_download_links(self, html: str, base_url: str) -> List[Dict[str, str]]:
        """Extract download links from book details page."""
        links = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for download buttons/links
            download_elements = soup.find_all(['a', 'button'], string=re.compile(r'download|get|mirror', re.I))
            
            for element in download_elements:
                href = element.get('href')
                if href:
                    if href.startswith('http'):
                        link_url = href
                    else:
                        link_url = urljoin(base_url, href)
                        
                    links.append({
                        'url': link_url,
                        'text': element.get_text(strip=True),
                        'mirror': base_url
                    })
                    
        except Exception as e:
            logger.error(f"Error extracting download links: {str(e)}")
            
        return links
        
    def _remove_duplicates(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate books based on MD5 hash or title+author."""
        seen_md5 = set()
        seen_books = set()
        unique_results = []
        
        for book in results:
            # Use MD5 hash as primary deduplication key
            md5_hash = book.get('md5')
            if md5_hash and md5_hash in seen_md5:
                continue
            elif md5_hash:
                seen_md5.add(md5_hash)
                
            # Fallback to title+author combination
            book_key = (book.get('title', '').lower().strip(), 
                       book.get('author', '').lower().strip())
            if book_key in seen_books:
                continue
                
            seen_books.add(book_key)
            unique_results.append(book)
            
        return unique_results


# Example usage and testing
async def test_search():
    """Test function for the LibGen searcher."""
    searcher = LibGenSearcher()
    
    test_queries = [
        "Python programming",
        "Clean Code Robert Martin",
        "1984 George Orwell"
    ]
    
    for query in test_queries:
        print(f"\n--- Testing search: {query} ---")
        results = await searcher.search(query, max_results=3)
        
        for i, book in enumerate(results, 1):
            print(f"{i}. {book['title']} by {book['author']} ({book['year']})")
            print(f"   Size: {book['size']} | Format: {book['extension']} | Pages: {book['pages']}")
            print(f"   MD5: {book.get('md5', 'N/A')}")
            

if __name__ == "__main__":
    # Run test
    asyncio.run(test_search())
