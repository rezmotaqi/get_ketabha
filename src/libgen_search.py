#!/usr/bin/env python3
"""
LibGen Search Module
Handles searching LibGen sites and extracting book information and download links.
"""

import asyncio
import aiohttp
import re
import os
import time
from typing import List, Dict, Any, Optional
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup
import logging
from dotenv import load_dotenv

from .utils.logger import setup_logger
from .utils.http_client import get_http_client, record_request_performance

# Load environment variables
load_dotenv()

logger = setup_logger(__name__)

class LibGenSearcher:
    """Main class for searching LibGen sites."""
    
    def __init__(self, timeout: int = None, max_retries: int = None):
        """Initialize the searcher."""
        # Load configuration from environment variables
        self.timeout = timeout or int(os.getenv('LIBGEN_SEARCH_TIMEOUT', '30'))
        self.max_retries = max_retries or int(os.getenv('LIBGEN_MAX_RETRIES', '1'))
        
        # Load mirrors from environment variables - Optimized for maximum reliability (Sep 2025)
        # Priority order: Most reliable and fastest mirrors first, with fallback tiers
        search_mirrors_env = os.getenv('LIBGEN_SEARCH_MIRRORS', 
                                       'https://libgen.la,https://libgen.li,https://libgen.gl,https://libgen.vg,https://libgen.bz,https://libgen.is,https://libgen.pw,https://libgen.ee,http://libgen.rs,http://gen.lib.rus.ec,https://libgen.fun,https://libgen.st')
        self.libgen_mirrors = [url.strip() for url in search_mirrors_env.split(',') if url.strip()]
        
        download_mirrors_env = os.getenv('LIBGEN_DOWNLOAD_MIRRORS', 
                                         'https://libgen.la,https://libgen.li,https://libgen.gl,https://libgen.vg,https://libgen.bz,https://libgen.is,https://libgen.pw,https://libgen.ee,http://libgen.rs,http://gen.lib.rus.ec,https://libgen.fun,https://libgen.st,http://library.lol,http://libgen.lc')
        self.download_mirrors = [url.strip() for url in download_mirrors_env.split(',') if url.strip()]
        
        # Mirror reliability tracking for intelligent fallback
        self.mirror_reliability = {}
        self.mirror_response_times = {}
        self.failed_mirrors = set()

        # Control whether to resolve get.php links to final URLs and filenames
        resolve_env = os.getenv('LIBGEN_RESOLVE_FINAL_URLS', 'true').strip().lower()
        self.resolve_final_urls = resolve_env in ['1', 'true', 'yes', 'on']
        
        # Initialize optimized HTTP client
        self.http_client = get_http_client()
        
        # Performance tracking
        self.search_stats = {
            'total_searches': 0,
            'successful_searches': 0,
            'failed_searches': 0,
            'average_search_time': 0.0,
            'mirror_performance': {}
        }
        
        # Simple in-memory cache for search results (TTL: 5 minutes)
        self.search_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        logger.info(f"Initialized with {len(self.libgen_mirrors)} search mirrors (Comprehensive Sep 2025): {', '.join(self.libgen_mirrors)}")
        logger.info(f"Initialized with {len(self.download_mirrors)} download mirrors (Comprehensive Sep 2025): {', '.join(self.download_mirrors)}")
        logger.info(f"Resolve final download URLs: {self.resolve_final_urls}")
        logger.info("Includes: Active mirrors, Russian LibGen mirrors, Anna's Archive, Z-Library, CyberLeninka")
        logger.info("Performance optimizations: Connection pooling, caching, performance tracking enabled")
        
    async def search(self, query: str, max_results: int = None) -> List[Dict[str, Any]]:
        """
        Search for books across LibGen mirrors with caching and performance optimization.
        
        Args:
            query: Search query (title, author, ISBN, etc.)
            max_results: Maximum number of results to return
            
        Returns:
            List of book dictionaries with metadata
        """
        # Use environment variable for max_results if not provided
        if max_results is None:
            max_results = int(os.getenv('LIBGEN_MAX_RESULTS', '200'))
            
        # Check if query is an MD5 hash (32 hex characters)
        import re
        if re.match(r'^[a-f0-9]{32}$', query.lower()):
            logger.info(f"🔍 MD5 hash detected: {query}")
            # For MD5 searches, try to get download links directly
            try:
                download_links = await self.get_download_links(query)
                if download_links:
                    # Create a mock book entry from the download links
                    book_entry = {
                        'title': f'Book with MD5: {query}',
                        'author': 'Unknown',
                        'year': 'Unknown',
                        'extension': 'Unknown',
                        'size': 'Unknown',
                        'md5': query,
                        'download_links': download_links
                    }
                    logger.info(f"✅ Found download links for MD5 {query}")
                    return [book_entry]
                else:
                    logger.warning(f"❌ No download links found for MD5 {query}")
                    return []
            except Exception as e:
                logger.error(f"❌ Error getting download links for MD5 {query}: {e}")
                return []
            
        # Check cache first
        cache_key = f"{query.lower().strip()}:{max_results}"
        current_time = time.time()
        
        if cache_key in self.search_cache:
            cached_data, cache_time = self.search_cache[cache_key]
            if current_time - cache_time < self.cache_ttl:
                logger.info(f"Cache hit for query: {query}")
                return cached_data
            else:
                # Remove expired cache entry
                del self.search_cache[cache_key]
        
        # Track search performance
        start_time = time.time()
        self.search_stats['total_searches'] += 1
        
        logger.info(f"Searching for: {query}")
        
        results = []
        
        # Get prioritized mirrors based on reliability and performance
        prioritized_mirrors = self._get_prioritized_mirrors()
        
        # SIMPLE SYNCHRONOUS SEARCH: Try mirrors one by one, return first result
        logger.info(f"🚀 Starting SIMPLE search - trying mirrors one by one...")
        
        for i, mirror in enumerate(prioritized_mirrors[:5]):  # Try first 5 mirrors
            logger.info(f"🔄 Attempt {i + 1}/5: Trying {mirror}...")
            
            try:
                # Search this mirror with 8-second timeout
                result = await asyncio.wait_for(
                    self._search_mirror_async(mirror, query),
                    timeout=8.0
                )
                
                if result and len(result) > 0:
                    results = result
                    logger.info(f"✅ SUCCESS! Got {len(result)} results from {mirror}")
                    break
                else:
                    logger.info(f"⚠️ No results from {mirror}, trying next...")
                    
            except asyncio.TimeoutError:
                logger.warning(f"⏰ Timeout on {mirror} (8s), trying next...")
                continue
            except Exception as e:
                logger.warning(f"❌ Error from {mirror}: {e}, trying next...")
                continue
                
        # Remove duplicates based on MD5 hash
        logger.info(f"🔄 Removing duplicates from {len(results)} results...")
        unique_results = self._remove_duplicates(results)
        final_results = unique_results[:max_results]
        logger.info(f"✅ Deduplication complete: {len(unique_results)} unique results, returning {len(final_results)}")
        
        # Log comprehensive search results
        total_found = len(results)
        unique_found = len(unique_results)
        returned = len(final_results)
        search_time = time.time() - start_time
        
        logger.info(f"Total results found: {total_found} from {len(self.libgen_mirrors)} mirrors")
        logger.info(f"Unique results after deduplication: {unique_found}")
        logger.info(f"Results returned: {returned} (limited by max_results={max_results})")
        logger.info(f"Search completed in {search_time:.2f}s for query: '{query}'")
        
        # Update performance stats
        total_time = time.time() - start_time
        if final_results:
            self.search_stats['successful_searches'] += 1
        else:
            self.search_stats['failed_searches'] += 1
            
        # Update average search time
        total_searches = self.search_stats['total_searches']
        current_avg = self.search_stats['average_search_time']
        self.search_stats['average_search_time'] = (
            (current_avg * (total_searches - 1) + total_time) / total_searches
        )
        
        # Cache the results
        self.search_cache[cache_key] = (final_results, current_time)
        
        # Clean up old cache entries
        self._cleanup_cache()
        
        logger.info(f"Total unique results: {len(final_results)} (search time: {total_time:.2f}s)")
        record_request_performance(f"search:{query}", total_time)
        
        return final_results
    
    def _cleanup_cache(self):
        """Remove expired cache entries."""
        current_time = time.time()
        expired_keys = [
            key for key, (_, cache_time) in self.search_cache.items()
            if current_time - cache_time > self.cache_ttl
        ]
        for key in expired_keys:
            del self.search_cache[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
        
    async def _search_mirror_async(self, mirror: str, query: str) -> List[Dict[str, Any]]:
        """Search a specific LibGen mirror asynchronously with reliability tracking."""
        search_url = f"{mirror}/index.php"
        params = {
            'req': query,
            'columns[]': ['t', 'a', 's', 'y', 'p', 'i'],  # Title, Author, Series, Year, Publisher, ISBN
            'objects[]': ['f', 'e', 's', 'a', 'p', 'w'],  # Files, Editions, Series, Authors, Publishers, Works
            'topics[]': ['l', 'c', 'f', 'a', 'm', 'r', 's'],  # All topics
            'res': str(int(os.getenv('LIBGEN_MIRROR_REQUEST_LIMIT', '1000'))),  # Search all available results
            'filesuns': 'all',
            'curtab': 'f'  # Files tab
        }
        
        # Use optimized HTTP client with SSL verification bypass for problematic mirrors
        ssl_verify = not any(problematic in mirror for problematic in ['libgen.fun', 'libgen.rs'])
        
        start_time = time.time()
        success = False
        response_time = 0
        
        for attempt in range(self.max_retries):
            try:
                response = self.http_client.get(search_url, params=params, verify=ssl_verify)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    html = response.text
                    results = self._parse_search_results(html, mirror)
                    success = True
                    logger.info(f"✅ Success from {mirror} in {response_time:.2f}s: {len(results)} results")
                    return results
                else:
                    logger.warning(f"HTTP {response.status_code} from {mirror}")
                    
            except Exception as e:
                response_time = time.time() - start_time
                logger.warning(f"Request error on attempt {attempt + 1} for {mirror}: {str(e)}")
                
            if attempt < self.max_retries - 1:
                await asyncio.sleep(1)  # Brief delay before retry
        
        # Update reliability tracking
        self._update_mirror_reliability(mirror, success, response_time)
        
        if not success:
            logger.warning(f"❌ All attempts failed for {mirror}")
        
        return []

    async def _search_mirror(self, mirror: str, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search a specific LibGen mirror using the correct index.php pattern."""
        search_url = f"{mirror}/index.php"
        params = {
            'req': query,
            'columns[]': ['t', 'a', 's', 'y', 'p', 'i'],  # Title, Author, Series, Year, Publisher, ISBN
            'objects[]': ['f', 'e', 's', 'a', 'p', 'w'],  # Files, Editions, Series, Authors, Publishers, Works
            'topics[]': ['l', 'c', 'f', 'a', 'm', 'r', 's'],  # All topics
            'res': str(int(os.getenv('LIBGEN_MIRROR_REQUEST_LIMIT', '1000'))),  # Search all available results
            'filesuns': 'all',
            'curtab': 'f'  # Files tab
        }
        
        # Use optimized HTTP client with SSL verification bypass for problematic mirrors
        ssl_verify = not any(problematic in mirror for problematic in ['libgen.fun', 'libgen.rs'])
        
        for attempt in range(self.max_retries):
            try:
                response = self.http_client.get(search_url, params=params, verify=ssl_verify)
                if response.status_code == 200:
                    html = response.text
                    return self._parse_search_results(html, mirror)
                else:
                    logger.warning(f"HTTP {response.status_code} from {mirror}")
                    
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
                    
                    # Try to extract MD5 from various sources
                    md5_hash = None
                    
                    for link in links:
                        href = link.get('href', '')
                        
                        # Look for MD5 hash in any URL parameter
                        md5_match = re.search(r'md5=([a-f0-9]{32})', href)
                        if md5_match and not md5_hash:
                            md5_hash = md5_match.group(1)
                            book_info['md5'] = md5_hash
                        
                        # Look for different types of download links
                        if '/ads.php?md5=' in href or 'md5=' in href:
                            # LibGen mirror with MD5
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
                    
                    # If no MD5 found in links, try to extract from other sources
                    if not md5_hash:
                        # Check if MD5 is in any cell content or data attributes
                        for cell in cells:
                            cell_text = cell.get_text()
                            cell_html = str(cell)
                            md5_match = re.search(r'\b([a-f0-9]{32})\b', cell_text + ' ' + cell_html)
                            if md5_match:
                                md5_hash = md5_match.group(1)
                                book_info['md5'] = md5_hash
                                break
                    
                    # Clean up data
                    book_info = self._clean_book_info(book_info)
                    
                    if book_info['title']:  # Must have title (author optional)
                        results.append(book_info)
                        
                except Exception as e:
                    logger.debug(f"Error parsing result row: {str(e)}")
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
        Tries mirrors one by one and returns first successful result.
        
        Args:
            md5_hash: MD5 hash of the book
            
        Returns:
            List of download link dictionaries
        """
        download_links = []
        
        # Try multiple mirrors to get diverse download sources
        print(f"🔗 Collecting links from multiple mirrors for variety...")
        successful_mirrors = 0
        max_mirrors = 5  # Try up to 5 mirrors for variety
        
        for i, mirror in enumerate(self.download_mirrors[:max_mirrors]):
            try:
                logger.info(f"🔗 Getting download links from mirror {i+1}/{max_mirrors}: {mirror}")
                print(f"🔗 Mirror {i+1}/{max_mirrors}: {mirror}")
                
                # Try to get final download links following LibGen's pattern
                links = await asyncio.wait_for(
                    self._get_final_download_links(mirror, md5_hash), 
                    timeout=3.0  # 3 seconds per mirror for speed
                )
                
                if links:
                    download_links.extend(links)
                    successful_mirrors += 1
                    logger.info(f"✅ Found {len(links)} download links from {mirror}")
                    print(f"✅ Found {len(links)} links from {mirror} (Total: {len(download_links)})")
                    
                    # If we have enough links from different sources, we can return early
                    if len(download_links) >= 8 and successful_mirrors >= 2:
                        print(f"🚀 Got {len(download_links)} links from {successful_mirrors} mirrors - returning diverse set")
                        break
                else:
                    logger.info(f"⚠️ No links from {mirror}, trying next...")
                    print(f"⚠️ No links from {mirror}, trying next...")
                
            except asyncio.TimeoutError:
                logger.warning(f"⏰ Timeout getting links from {mirror}, trying next...")
                print(f"⏰ Timeout from {mirror}, trying next...")
                continue
            except Exception as e:
                logger.warning(f"❌ Error getting links from {mirror}: {str(e)}, trying next...")
                print(f"❌ Error from {mirror}: {str(e)}, trying next...")
                continue
        
        print(f"🎯 Final result: {len(download_links)} links from {successful_mirrors} mirrors")
        
        logger.info(f"🎯 No links found from any mirror, trying additional sources...")
        
        # If no links found from mirrors, try additional sources
        additional_links = await self._get_additional_download_sources(md5_hash)
        
        # Test additional links before adding them
        verified_additional_links = []
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10.0)) as session:
            for link in additional_links:
                if await self._test_download_link(session, link['url']):
                    verified_additional_links.append(link)
                    logger.info(f"✅ Verified additional link: {link['name']}")
                else:
                    logger.info(f"❌ Additional link failed verification: {link['name']}")
        
        download_links.extend(verified_additional_links)
                
        return download_links
        
    async def _get_additional_download_sources(self, md5_hash: str) -> List[Dict[str, str]]:
        """Get additional download sources for a book using various methods."""
        additional_links = []
        
        # Add Library.lol direct links with multiple variants
        library_lol_links = [
            f"http://library.lol/main/{md5_hash}",
            f"https://library.lol/main/{md5_hash}",
            f"http://libgen.lc/main/{md5_hash}",
            f"https://libgen.lc/main/{md5_hash}",
            f"http://libgen.lc/book/index.php?md5={md5_hash}",
            f"https://libgen.lc/book/index.php?md5={md5_hash}",
            f"http://libgen.lc/get.php?md5={md5_hash}",
            f"https://libgen.lc/get.php?md5={md5_hash}",
        ]
        
        for i, url in enumerate(library_lol_links):
            additional_links.append({
                'url': url,
                'type': 'library_lol',
                'name': f'Library.lol {i+1}',
                'text': f'Library.lol Variant {i+1}'
            })
        
        # Add Anna's Archive links (Rank #2 - Meta-search engine aggregating LibGen, Sci-Hub, Z-Library)
        annas_archive_links = [
            f"https://annas-archive.org/md5/{md5_hash}",
            f"https://annas-archive.li/md5/{md5_hash}",
            f"https://annas-archive.se/md5/{md5_hash}",
            f"https://annas-archive.org/md5/{md5_hash}",
            f"https://annas-archive.li/md5/{md5_hash}",
        ]
        
        for i, url in enumerate(annas_archive_links):
            additional_links.append({
                'url': url,
                'type': 'annas_archive',
                'name': f"Anna's Archive {i+1}",
                'text': "Meta-Search Engine"
            })
        
        # Add Z-Library links (Rank #3 - Large database, good performance)
        z_lib_links = [
            f"https://z-library.sk/md5/{md5_hash}",
            f"https://z-lib.org/md5/{md5_hash}",
            f"https://b-ok.org/md5/{md5_hash}",
            f"https://booksc.eu/md5/{md5_hash}",
        ]
        
        for i, url in enumerate(z_lib_links):
            additional_links.append({
                'url': url,
                'type': 'z_library',
                'name': f'Z-Library {i+1}',
                'text': 'Comprehensive Shadow Library'
            })
        
        # Add Ocean of PDF links (Rank #4 - Clean interface, quick downloads)
        ocean_pdf_links = [
            f"https://oceanofpdf.com/?s={md5_hash}",
            f"https://oceanofpdf.com/search/{md5_hash}",
        ]
        
        for i, url in enumerate(ocean_pdf_links):
            additional_links.append({
                'url': url,
                'type': 'ocean_pdf',
                'name': f'Ocean of PDF {i+1}',
                'text': 'Clean Interface'
            })
        
        # Add Liber3 links (Rank #5 - Fast and typically ad-free)
        liber3_links = [
            f"https://liber3.eth.limo/search?q={md5_hash}",
        ]
        
        for url in liber3_links:
            additional_links.append({
                'url': url,
                'type': 'liber3',
                'name': 'Liber3',
                'text': 'Fast & Ad-Free'
            })
        
        # Add Memory of the World links (Rank #6 - Solid fallback option)
        memory_world_links = [
            f"https://library.memoryoftheworld.org/search?q={md5_hash}",
            f"https://library.memoryoftheworld.org/md5/{md5_hash}",
        ]
        
        for i, url in enumerate(memory_world_links):
            additional_links.append({
                'url': url,
                'type': 'memory_world',
                'name': f'Memory of the World {i+1}',
                'text': 'Minimal Overhead'
            })
        
        # Add Sci-Hub links (Rank #7 - Academic papers and books)
        scihub_links = [
            f"https://sci-hub.se/{md5_hash}",
            f"https://sci-hub.st/{md5_hash}",
            f"https://sci-hub.ru/{md5_hash}",
        ]
        
        for i, url in enumerate(scihub_links):
            additional_links.append({
                'url': url,
                'type': 'scihub',
                'name': f'Sci-Hub {i+1}',
                'text': 'Academic Papers'
            })
        
        # Add direct download links (Rank #8 - Direct file access)
        direct_links = [
            f"https://libgen.lc/get.php?md5={md5_hash}",
            f"http://libgen.lc/get.php?md5={md5_hash}",
            f"https://library.lol/get.php?md5={md5_hash}",
            f"http://library.lol/get.php?md5={md5_hash}",
        ]
        
        for i, url in enumerate(direct_links):
            additional_links.append({
                'url': url,
                'type': 'direct_download',
                'name': f'Direct Download {i+1}',
                'text': 'Direct File Access'
            })
        
        # Add direct LibGen mirror links (Updated September 2025 - comprehensive list)
        libgen_direct_links = [
            # Active Mirrors (Sep 2025) - Primary
            f"https://libgen.li/book/index.php?md5={md5_hash}",
            f"https://libgen.la/book/index.php?md5={md5_hash}",
            f"https://libgen.gl/book/index.php?md5={md5_hash}",
            f"https://libgen.vg/book/index.php?md5={md5_hash}",
            f"https://libgen.bz/book/index.php?md5={md5_hash}",
            f"https://libgen.is/book/index.php?md5={md5_hash}",
            # Russian LibGen-related Mirrors
            f"http://libgen.rs/book/index.php?md5={md5_hash}",
            f"http://gen.lib.rus.ec/book/index.php?md5={md5_hash}",
            f"https://libgen.fun/book/index.php?md5={md5_hash}",
        ]
        
        for url in libgen_direct_links:
            additional_links.append({
                'url': url,
                'type': 'libgen_direct',
                'name': 'LibGen Direct',
                'text': 'LibGen Mirror'
            })
        
        # Add CyberLeninka (Legal Russian Repository for scientific papers)
        cyberleninka_links = [
            f"https://cyberleninka.ru/search?q={md5_hash}",
        ]
        
        for url in cyberleninka_links:
            additional_links.append({
                'url': url,
                'type': 'cyberleninka',
                'name': 'CyberLeninka',
                'text': 'Legal Russian Repository'
            })
        
        return additional_links
    
    async def _test_download_link(self, session: aiohttp.ClientSession, url: str, referer: str = None) -> bool:
        """
        Test if a download link actually resolves to a real file.
        Returns True if the link works, False otherwise.
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            if referer:
                headers['Referer'] = referer
            
            # Make a HEAD request to check if the link resolves
            async with session.head(url, headers=headers, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=5.0)) as response:
                # Check if we get a successful response and it's not an error page
                if response.status == 200:
                    content_type = response.headers.get('Content-Type', '').lower()
                    content_length = response.headers.get('Content-Length', '0')
                    
                    # Check if it looks like a real file (not HTML error page)
                    if 'text/html' not in content_type and int(content_length) > 0:
                        return True
                    # Also accept if it's a redirect to a file
                    elif 'application/' in content_type or 'text/plain' in content_type:
                        return True
                
                return False
                
        except Exception as e:
            logger.debug(f"Link test failed for {url}: {e}")
            return False
        
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
            logger.info(f"🔗 Step 1: Accessing ads.php for {md5_hash} on {mirror}")
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10.0)) as session:
                # Get the ads.php page (might redirect)
                logger.info(f"🔗 Step 2: Making GET request to {ads_url}")
                async with session.get(ads_url) as response:
                    logger.info(f"🔗 Step 3: Got response status {response.status}")
                    if response.status != 200:
                        logger.warning(f"🔗 Step 4: Bad response status {response.status}, returning empty")
                        return download_links
                        
                    logger.info(f"🔗 Step 5: Reading response text...")
                    html = await response.text()
                    logger.info(f"🔗 Step 6: Got {len(html)} characters of HTML")
                    final_url = str(response.url)  # Get final URL after redirects
                    
                    # Parse the final page for download links
                    logger.info(f"🔗 Step 7: Parsing HTML with BeautifulSoup...")
                    soup = BeautifulSoup(html, 'html.parser')
                    logger.info(f"🔗 Step 8: BeautifulSoup parsing complete")
                    
                    # Prefer any direct mirrors first (Cloudflare/IPFS/CDN endpoints) if present
                    direct_patterns = [
                        r'https?://(?:[\w.-]*cloudflare|cfcdn)[\w.-]*/[^\s\"]+',
                        r'https?://ipfs\.[\w.-]+/[^\s\"]+',
                        r'https?://(?:[\w.-]*cdn)[\w.-]*/[^\s\"]+'
                    ]
                    direct_links: List[Dict[str, str]] = []
                    for pattern in direct_patterns:
                        for a in soup.find_all('a', href=re.compile(pattern, re.I)):
                            href = a.get('href')
                            if not href:
                                continue
                            direct_links.append({
                                'url': href,
                                'type': 'direct_mirror',
                                'name': 'Direct Mirror',
                                'text': a.get_text(strip=True) or 'Direct Mirror'
                            })

                    # If we found direct links, optionally resolve and return them with priority
                    if direct_links:
                        resolved_direct: List[Dict[str, str]] = []
                        for dl in direct_links:
                            resolved_url = dl['url']
                            filename = None
                            content_type = None
                            if self.resolve_final_urls:
                                try:
                                    resolution = await self._resolve_download_link(session, dl['url'], referer=final_url)
                                    resolved_url = resolution.get('final_url') or dl['url']
                                    filename = resolution.get('filename')
                                    content_type = resolution.get('content_type')
                                except Exception:
                                    pass
                            link_dict = {**dl, 'url': resolved_url}
                            if filename:
                                link_dict['filename'] = filename
                            if content_type:
                                link_dict['content_type'] = content_type
                            resolved_direct.append(link_dict)
                        download_links.extend(resolved_direct)

                    # Look for the main GET button/link (pattern: get.php?md5=hash&key=key)
                    logger.info(f"🔗 Step 9: Looking for get.php links...")
                    get_links = soup.find_all('a', href=re.compile(r'get\.php\?md5=[a-f0-9]{32}&key=\w+'))
                    logger.info(f"🔗 Step 10: Found {len(get_links)} get.php links")
                    
                    logger.info(f"🔗 Step 11: Processing {len(get_links)} get.php links...")
                    for i, link in enumerate(get_links):
                        logger.info(f"🔗 Step 11.{i+1}: Processing link {i+1}/{len(get_links)}")
                        href = link.get('href')
                        logger.info(f"🔗 Step 11.{i+1}.1: Got href: {href}")
                        if href:
                            if href.startswith('http'):
                                final_download_url = href
                            else:
                                final_download_url = urljoin(final_url, href)
                            
                            # Skip URL resolution to prevent timeouts - use original URL directly
                            logger.info(f"🔗 Step 11.{i+1}.2: Skipping URL resolution to prevent timeouts")
                            filename = None
                            resolved_url = final_download_url
                            content_type = None
                            
                            # Create multiple link variants for better user experience
                            base_url = final_download_url
                            
                            # 1. Test and add original link only if it works
                            if await self._test_download_link(session, resolved_url, final_url):
                                link_dict: Dict[str, str] = {
                                    'url': resolved_url,
                                    'type': 'direct_download',
                                    'name': 'Direct Download',
                                    'text': link.get_text(strip=True)
                                }
                                if filename:
                                    link_dict['filename'] = filename
                                if content_type:
                                    link_dict['content_type'] = content_type
                                download_links.append(link_dict)
                                logger.info(f"✅ Verified primary link: {mirror}")
                            else:
                                logger.info(f"❌ Primary link failed verification: {mirror}")
                            
                            # 2. Create links to other mirrors for true diversity
                            try:
                                from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
                                parsed = urlparse(base_url)
                                if 'get.php' in parsed.path:
                                    # Parse existing parameters
                                    query_params = parse_qs(parsed.query)
                                    md5_hash = query_params.get('md5', [''])[0]
                                    
                                    if md5_hash:
                                        # Create links to other mirrors for true diversity
                                        other_mirrors = [
                                            'https://libgen.li', 'https://libgen.gl', 'https://libgen.vg', 
                                            'https://libgen.bz', 'https://libgen.is', 'https://libgen.pw',
                                            'https://libgen.ee', 'http://libgen.rs', 'http://gen.lib.rus.ec',
                                            'https://libgen.fun', 'https://libgen.st', 'http://library.lol'
                                        ]
                                        
                                        # Get current mirror domain to avoid duplicates
                                        current_domain = parsed.netloc
                                        
                                        # Test each mirror link before adding it
                                        mirror_links = []
                                        for other_mirror in other_mirrors:
                                            if other_mirror not in mirror and other_mirror.split('://')[1] != current_domain:
                                                # Create direct download link for other mirror
                                                other_url = f"{other_mirror}/get.php?md5={md5_hash}&key={query_params.get('key', [''])[0]}"
                                                
                                                # Test if the link resolves to a real file
                                                if await self._test_download_link(session, other_url, final_url):
                                                    mirror_links.append({
                                                        'url': other_url,
                                                        'type': 'mirror_download',
                                                        'name': f'Mirror ({other_mirror.split("://")[1]})',
                                                        'text': f'Mirror: {other_mirror.split("://")[1]}'
                                                    })
                                                    logger.info(f"✅ Verified working link: {other_mirror}")
                                                else:
                                                    logger.info(f"❌ Link failed verification: {other_mirror}")
                                        
                                        # Add verified mirror links (up to 7)
                                        download_links.extend(mirror_links[:7])
                                        
                                        # Limit to 8 alternatives per source for more options
                                        if len([l for l in download_links if l['type'] == 'alternative_download']) >= 8:
                                            break
                            except Exception as e:
                                logger.warning(f"Error creating alternative URLs: {e}")
                                pass
                            
                    # Also look for alternative download links
                    alt_links = soup.find_all('a', href=re.compile(r'/file\.php\?id=\d+'))
                    for link in alt_links:
                        href = link.get('href')
                        if href:
                            if href.startswith('http'):
                                alt_url = href
                            else:
                                alt_url = urljoin(final_url, href)
                            
                            # Optionally resolve alt link
                            filename = None
                            resolved_url = alt_url
                            content_type = None
                            if self.resolve_final_urls:
                                try:
                                    resolution = await self._resolve_download_link(session, alt_url, referer=final_url)
                                    resolved_url = resolution.get('final_url') or alt_url
                                    filename = resolution.get('filename')
                                    content_type = resolution.get('content_type')
                                except Exception as _:
                                    pass
                            
                            alt_dict: Dict[str, str] = {
                                'url': resolved_url,
                                'type': 'file_download',
                                'name': 'Alternative Download',
                                'text': link.get_text(strip=True)
                            }
                            if filename:
                                alt_dict['filename'] = filename
                            if content_type:
                                alt_dict['content_type'] = content_type
                            download_links.append(alt_dict)
                            
        except Exception as e:
            logger.debug(f"Error getting final download links from {mirror}: {str(e)}")
            
        return download_links
        
    async def _get_download_links_from_mirror(self, mirror: str, md5_hash: str) -> List[Dict[str, str]]:
        """Get download links from a specific mirror."""
        download_urls = []
        
        # Try different URL patterns for the mirror
        url_patterns = [
            f"{mirror}/main/{md5_hash}",
            f"{mirror}/book/index.php?md5={md5_hash}",
        ]
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10.0)) as session:
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
                    logger.debug(f"Error fetching {url}: {str(e)}")
                    continue
                    
        return download_urls
        
    async def _resolve_download_link(self, session: aiohttp.ClientSession, url: str, referer: Optional[str] = None) -> Dict[str, Any]:
        """Resolve a download link to its final URL and extract filename without downloading the file.

        Tries HEAD first; if not allowed, performs a ranged GET (first byte) to avoid large transfers.
        """
        headers = {
            'User-Agent': os.getenv('HTTP_USER_AGENT', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36')
        }
        if referer:
            headers['Referer'] = referer
        try:
            async with session.head(url, headers=headers, allow_redirects=True) as resp:
                final_url = str(resp.url)
                disposition = resp.headers.get('Content-Disposition', '')
                filename = self._extract_filename_from_disposition(disposition) or self._infer_filename_from_url(final_url)
                return {
                    'final_url': final_url,
                    'filename': filename,
                    'content_type': resp.headers.get('Content-Type')
                }
        except Exception:
            # Fallback to a ranged GET request
            ranged_headers = {**headers, 'Range': 'bytes=0-0'}
            async with session.get(url, headers=ranged_headers, allow_redirects=True) as resp:
                final_url = str(resp.url)
                disposition = resp.headers.get('Content-Disposition', '')
                filename = self._extract_filename_from_disposition(disposition) or self._infer_filename_from_url(final_url)
                try:
                    await resp.release()
                except Exception:
                    pass
                return {
                    'final_url': final_url,
                    'filename': filename,
                    'content_type': resp.headers.get('Content-Type')
                }

    def _extract_filename_from_disposition(self, content_disposition: str) -> Optional[str]:
        """Extract filename from Content-Disposition header if present."""
        if not content_disposition:
            return None
        # Try RFC 5987 filename*
        match_ext = re.search(r"filename\*=(?:UTF-8''|)\s*([^;]+)", content_disposition, flags=re.IGNORECASE)
        if match_ext:
            filename = match_ext.group(1)
            try:
                # Handle percent-encoding
                from urllib.parse import unquote
                return unquote(filename.strip('"'))
            except Exception:
                return filename.strip('"')
        # Fallback to filename=
        match = re.search(r'filename="?([^";]+)"?', content_disposition, flags=re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def _infer_filename_from_url(self, url: str) -> Optional[str]:
        """Infer a reasonable filename from the URL path if possible."""
        try:
            from urllib.parse import urlparse, unquote
            path = urlparse(url).path
            if not path:
                return None
            name = os.path.basename(path)
            name = unquote(name)
            if not name or '.' not in name:
                return None
            return name
        except Exception:
            return None
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

    def _get_prioritized_mirrors(self) -> List[str]:
        """
        Get mirrors in priority order based on reliability and performance.
        Excludes recently failed mirrors and prioritizes fast, reliable ones.
        """
        # Filter out recently failed mirrors (exclude for 5 minutes)
        current_time = time.time()
        available_mirrors = []
        
        for mirror in self.libgen_mirrors:
            if mirror not in self.failed_mirrors:
                available_mirrors.append(mirror)
            else:
                # Check if enough time has passed to retry this mirror
                if current_time - self.mirror_reliability.get(mirror, {}).get('last_failure', 0) > 300:  # 5 minutes
                    available_mirrors.append(mirror)
                    self.failed_mirrors.discard(mirror)
        
        # Sort by reliability score (higher is better)
        def reliability_score(mirror):
            reliability_data = self.mirror_reliability.get(mirror, {})
            success_rate = reliability_data.get('success_rate', 0.5)  # Default 50%
            avg_response_time = self.mirror_response_times.get(mirror, 10.0)  # Default 10s
            
            # Calculate score: success_rate * 100 - avg_response_time
            # Higher success rate and lower response time = better score
            score = (success_rate * 100) - (avg_response_time * 0.1)
            return score
        
        available_mirrors.sort(key=reliability_score, reverse=True)
        
        # If we have very few available mirrors, include some failed ones as fallback
        if len(available_mirrors) < 3:
            fallback_mirrors = [m for m in self.libgen_mirrors if m not in available_mirrors]
            available_mirrors.extend(fallback_mirrors[:3])
        
        logger.info(f"Using {len(available_mirrors)} mirrors in priority order")
        return available_mirrors

    def _update_mirror_reliability(self, mirror: str, success: bool, response_time: float):
        """
        Update mirror reliability statistics for intelligent fallback.
        
        Args:
            mirror: Mirror URL
            success: Whether the request was successful
            response_time: Response time in seconds
        """
        current_time = time.time()
        
        if mirror not in self.mirror_reliability:
            self.mirror_reliability[mirror] = {
                'total_requests': 0,
                'successful_requests': 0,
                'success_rate': 0.5,  # Start with 50% assumption
                'last_failure': 0,
                'last_success': current_time
            }
        
        reliability_data = self.mirror_reliability[mirror]
        reliability_data['total_requests'] += 1
        reliability_data['last_success'] = current_time
        
        if success:
            reliability_data['successful_requests'] += 1
            # Remove from failed mirrors if it was there
            self.failed_mirrors.discard(mirror)
        else:
            reliability_data['last_failure'] = current_time
            # Add to failed mirrors
            self.failed_mirrors.add(mirror)
        
        # Update success rate
        reliability_data['success_rate'] = (
            reliability_data['successful_requests'] / reliability_data['total_requests']
        )
        
        # Update response time (exponential moving average)
        if mirror in self.mirror_response_times:
            self.mirror_response_times[mirror] = (
                0.7 * self.mirror_response_times[mirror] + 0.3 * response_time
            )
        else:
            self.mirror_response_times[mirror] = response_time

    def _get_mirror_status(self) -> Dict[str, Any]:
        """
        Get current mirror status for monitoring and debugging.
        
        Returns:
            Dictionary with mirror status information
        """
        status = {
            'total_mirrors': len(self.libgen_mirrors),
            'available_mirrors': len(self._get_prioritized_mirrors()),
            'failed_mirrors': len(self.failed_mirrors),
            'mirror_details': {}
        }
        
        for mirror in self.libgen_mirrors:
            reliability_data = self.mirror_reliability.get(mirror, {})
            status['mirror_details'][mirror] = {
                'success_rate': reliability_data.get('success_rate', 0.5),
                'total_requests': reliability_data.get('total_requests', 0),
                'avg_response_time': self.mirror_response_times.get(mirror, 0),
                'is_failed': mirror in self.failed_mirrors,
                'last_success': reliability_data.get('last_success', 0),
                'last_failure': reliability_data.get('last_failure', 0)
            }
        
        return status


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
