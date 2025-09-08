#!/usr/bin/env python3
"""
LibGen Search Module
Handles searching LibGen sites and extracting book information and download links.
"""

import asyncio
import aiohttp
import re
import os
from typing import List, Dict, Any, Optional
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup
import logging
from dotenv import load_dotenv

from utils.logger import setup_logger

# Load environment variables
load_dotenv()

logger = setup_logger(__name__)

class LibGenSearcher:
    """Main class for searching LibGen sites."""
    
    def __init__(self, timeout: int = 30, max_retries: int = 1):
        """Initialize the searcher."""
        self.timeout = timeout
        self.max_retries = max_retries  # Now used per mirror, not total
        
        # Load mirrors from environment variables
        search_mirrors_env = os.getenv('LIBGEN_SEARCH_MIRRORS', 
                                       'http://libgen.rs,http://libgen.is,https://libgen.la,http://libgen.st,https://libgen.fun')
        self.libgen_mirrors = [url.strip() for url in search_mirrors_env.split(',') if url.strip()]
        
        download_mirrors_env = os.getenv('LIBGEN_DOWNLOAD_MIRRORS', 
                                         'http://library.lol,http://libgen.rs,http://libgen.is,https://libgen.la')
        self.download_mirrors = [url.strip() for url in download_mirrors_env.split(',') if url.strip()]
        
        logger.info(f"Initialized with {len(self.libgen_mirrors)} search mirrors: {', '.join(self.libgen_mirrors)}")
        logger.info(f"Initialized with {len(self.download_mirrors)} download mirrors: {', '.join(self.download_mirrors)}")
        
    async def search(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
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
        
        # Try each mirror once until we get results
        for mirror in self.libgen_mirrors:
            try:
                logger.info(f"Attempting search on mirror: {mirror}")
                mirror_results = await self._search_mirror(mirror, query, max_results)
                if mirror_results:
                    results.extend(mirror_results)
                    logger.info(f"Found {len(mirror_results)} results from {mirror}")
                    break
                else:
                    logger.info(f"No results from {mirror}, trying next mirror")
                    
            except Exception as e:
                logger.warning(f"Failed to search {mirror}: {str(e)}")
                continue
                
        # Remove duplicates based on MD5 hash
        unique_results = self._remove_duplicates(results)
        
        logger.info(f"Total unique results: {len(unique_results)}")
        return unique_results[:max_results]
        
    async def _search_mirror(self, mirror: str, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search a specific LibGen mirror using the correct index.php pattern."""
        search_url = f"{mirror}/index.php"
        params = {
            'req': query,
            'columns[]': ['t', 'a', 's', 'y', 'p', 'i'],  # Title, Author, Series, Year, Publisher, ISBN
            'objects[]': ['f', 'e', 's', 'a', 'p', 'w'],  # Files, Editions, Series, Authors, Publishers, Works
            'topics[]': ['l', 'c', 'f', 'a', 'm', 'r', 's'],  # All topics
            'res': str(min(max_results, 100)),
            'filesuns': 'all',
            'curtab': 'f'  # Files tab
        }
        
        # Configure proxy if available
        proxy = os.getenv('HTTP_PROXY') or os.getenv('HTTPS_PROXY')
        
        connector = None
        if proxy:
            connector = aiohttp.TCPConnector()
            
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            connector=connector
        ) as session:
            for attempt in range(self.max_retries):
                try:
                    async with session.get(search_url, params=params, proxy=proxy) as response:
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
            
            # Find results table - LibGen uses table with id='tablelibgen'
            table = soup.find('table', {'id': 'tablelibgen'}) or soup.find('table', {'class': 'table table-striped'})
            if not table:
                return results
                
            # Get table body rows
            tbody = table.find('tbody')
            if tbody:
                rows = tbody.find_all('tr')
            else:
                rows = table.find_all('tr')[1:]  # Skip header row if no tbody
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 9:  # LibGen has 9 columns: Title/Series, Author, Publisher, Year, Language, Pages, Size, Ext, Mirrors
                    continue
                    
                try:
                    # Extract title and series from first cell (complex structure)
                    title_cell = cells[0]
                    title_text = title_cell.get_text(strip=True)
                    
                    # Try to extract title from the cell structure - improved parsing
                    title_links = title_cell.find_all('a')
                    if title_links:
                        # Try different approaches to get the actual title
                        for link in title_links:
                            link_text = link.get_text(strip=True)
                            if link_text and len(link_text) > 2 and link_text != 'b':
                                title = link_text
                                break
                        else:
                            # Fallback to the full cell text if links don't work
                            title = title_text if title_text and len(title_text) > 2 else "Unknown Title"
                    else:
                        title = title_text if title_text and len(title_text) > 2 else "Unknown Title"
                    
                    # Extract book information based on LibGen's actual structure
                    book_info = {
                        'title': title,
                        'author': cells[1].get_text(strip=True),
                        'publisher': cells[2].get_text(strip=True),
                        'year': cells[3].get_text(strip=True),
                        'language': cells[4].get_text(strip=True),
                        'pages': cells[5].get_text(strip=True),
                        'size': cells[6].get_text(strip=True),
                        'extension': cells[7].get_text(strip=True),
                        'mirrors': []
                    }
                    
                    # Extract MD5 hash and download links from the mirrors column
                    mirrors_cell = cells[8]
                    links = mirrors_cell.find_all('a')
                    
                    for link in links:
                        href = link.get('href', '')
                        
                        # Look for different types of download links
                        if '/ads.php?md5=' in href:
                            # LibGen mirror 1 (ads.php)
                            md5_match = re.search(r'md5=([a-f0-9]{32})', href)
                            if md5_match:
                                book_info['md5'] = md5_match.group(1)
                                book_info['mirrors'].append({
                                    'url': urljoin(base_url, href),
                                    'type': 'libgen_mirror_1',
                                    'name': 'LibGen Mirror 1'
                                })
                                
                        elif 'randombook.org' in href:
                            # RandomBook mirror
                            book_info['mirrors'].append({
                                'url': href,
                                'type': 'randombook',
                                'name': 'RandomBook'
                            })
                            
                        elif 'annas-archive.org' in href:
                            # Anna's Archive mirror
                            book_info['mirrors'].append({
                                'url': href,
                                'type': 'annas_archive',
                                'name': "Anna's Archive"
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
        Follows the LibGen pattern: ads.php -> file details page -> get.php final download
        
        Args:
            md5_hash: MD5 hash of the book
            
        Returns:
            List of download link dictionaries
        """
        download_links = []
        
        for mirror in self.download_mirrors:
            try:
                # Try to get final download links following LibGen's pattern
                links = await self._get_final_download_links(mirror, md5_hash)
                download_links.extend(links)
                
                # Also try the old method as fallback
                fallback_links = await self._get_download_links_from_mirror(mirror, md5_hash)
                download_links.extend(fallback_links)
                
            except Exception as e:
                logger.warning(f"Failed to get download links from {mirror}: {str(e)}")
                continue
                
        return download_links
        
    async def _get_final_download_links(self, mirror: str, md5_hash: str) -> List[Dict[str, str]]:
        """
        Get final download links by following LibGen's pattern:
        1. Go to ads.php?md5=hash (mirror redirect page)
        2. Follow to file details page
        3. Extract final get.php download link with key
        """
        download_links = []
        
        try:
            # Step 1: Go to the ads.php redirect page
            ads_url = f"{mirror}/ads.php?md5={md5_hash}"
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                # Get the ads.php page (might redirect)
                async with session.get(ads_url) as response:
                    if response.status != 200:
                        return download_links
                        
                    html = await response.text()
                    final_url = str(response.url)  # Get final URL after redirects
                    
                    # Parse the final page for download links
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Look for the main GET button/link (pattern: get.php?md5=hash&key=key)
                    get_links = soup.find_all('a', href=re.compile(r'get\.php\?md5=[a-f0-9]{32}&key=\w+'))
                    
                    for link in get_links:
                        href = link.get('href')
                        if href:
                            if href.startswith('http'):
                                final_download_url = href
                            else:
                                final_download_url = urljoin(final_url, href)
                                
                            download_links.append({
                                'url': final_download_url,
                                'type': 'direct_download',
                                'name': 'Direct Download',
                                'text': link.get_text(strip=True)
                            })
                            
                    # Also look for alternative download links
                    alt_links = soup.find_all('a', href=re.compile(r'/file\.php\?id=\d+'))
                    for link in alt_links:
                        href = link.get('href')
                        if href:
                            if href.startswith('http'):
                                alt_url = href
                            else:
                                alt_url = urljoin(final_url, href)
                                
                            download_links.append({
                                'url': alt_url,
                                'type': 'file_download',
                                'name': 'Alternative Download',
                                'text': link.get_text(strip=True)
                            })
                            
        except Exception as e:
            logger.warning(f"Error getting final download links from {mirror}: {str(e)}")
            
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
