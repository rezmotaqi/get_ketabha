#!/usr/bin/env python3
"""
Concurrent File Handler
Non-blocking file download handler that allows true concurrent processing
"""

import asyncio
import aiohttp
import os
import mimetypes
import magic
from typing import Optional, Dict, Any, List, Tuple
from io import BytesIO
import logging
from urllib.parse import urlparse, unquote
import re
import time

from .logger import setup_logger

logger = setup_logger(__name__)

class ConcurrentFileHandler:
    """Non-blocking file handler for concurrent downloads."""
    
    # Valid book file extensions and their MIME types
    VALID_EXTENSIONS = {
        'pdf': ['application/pdf'],
        'epub': ['application/epub+zip', 'application/x-epub+zip'],
        'mobi': ['application/x-mobipocket-ebook', 'application/vnd.amazon.ebook'],
        'azw3': ['application/vnd.amazon.ebook'],
        'djvu': ['image/vnd.djvu', 'image/x-djvu'],
        'txt': ['text/plain'],
        'doc': ['application/msword'],
        'docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
        'rtf': ['application/rtf', 'text/rtf'],
        'fb2': ['application/x-fictionbook+xml', 'text/xml'],
        'lit': ['application/x-ms-reader'],
        'pdb': ['application/vnd.palm', 'application/x-palm-database'],
        'chm': ['application/vnd.ms-htmlhelp', 'application/x-chm'],
    }
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize concurrent file handler."""
        self.config = config
        self.min_size_mb = float(config.get('FILE_MIN_SIZE_MB', 0.1))
        self.max_size_mb = float(config.get('FILE_MAX_SIZE_MB', 50))
        self.min_size_bytes = int(self.min_size_mb * 1024 * 1024)
        self.max_size_bytes = int(self.max_size_mb * 1024 * 1024)
        self.download_timeout = int(config.get('FILE_DOWNLOAD_TIMEOUT', 60))
        self.retry_attempts = int(config.get('FILE_RETRY_ATTEMPTS', 2))
        self.user_agent = config.get('HTTP_USER_AGENT', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36')
        
        # Track concurrent downloads
        self.active_downloads = {}
        self.download_stats = {
            'total_downloads': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'total_size_mb': 0.0
        }
    
    async def get_best_file_from_links(self, download_links: List[Dict[str, str]], book_title: str = None) -> Optional[Dict[str, Any]]:
        """
        Try to download and validate files from multiple download links concurrently.
        Returns the best valid file found.
        """
        if not download_links:
            return None
        
        # Sort links by priority
        sorted_links = sorted(download_links, key=lambda x: self._get_link_priority(x))
        
        logger.info(f"Starting concurrent download from {len(sorted_links)} links")
        print(f"📥 Starting concurrent download from {len(sorted_links)} links...")
        
        # Create download tasks for concurrent execution
        download_tasks = []
        for i, link in enumerate(sorted_links[:5]):  # Limit to first 5 links for speed
            url = link.get('url', '')
            if url:
                task = asyncio.create_task(
                    self._download_file_concurrent(url, f"link_{i+1}")
                )
                download_tasks.append((task, link))
        
        if not download_tasks:
            return None
        
        # Wait for the first successful download
        try:
            done, pending = await asyncio.wait(
                [task for task, _ in download_tasks],
                return_when=asyncio.FIRST_COMPLETED,
                timeout=self.download_timeout
            )
            
            # Cancel remaining tasks
            for task, _ in download_tasks:
                if task not in done:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            # Get the first successful result
            for task, link in download_tasks:
                if task in done:
                    try:
                        result = await task
                        if result:
                            logger.info(f"Successfully downloaded file from {link.get('url', '')[:50]}...")
                            return result
                    except Exception as e:
                        logger.warning(f"Download task failed: {e}")
            
            return None
            
        except asyncio.TimeoutError:
            logger.warning("Download timeout - no files downloaded successfully")
            return None
    
    async def _download_file_concurrent(self, url: str, task_id: str) -> Optional[Dict[str, Any]]:
        """Download file concurrently without blocking the event loop."""
        start_time = time.time()
        
        try:
            # Use asyncio.to_thread for the blocking download operation
            result = await asyncio.to_thread(
                self._download_file_sync, url, task_id
            )
            
            download_time = time.time() - start_time
            
            if result:
                self.download_stats['successful_downloads'] += 1
                file_size_mb = result['size'] / (1024 * 1024)
                self.download_stats['total_size_mb'] += file_size_mb
                logger.info(f"Download {task_id} completed: {file_size_mb:.2f}MB in {download_time:.2f}s")
            else:
                self.download_stats['failed_downloads'] += 1
                logger.warning(f"Download {task_id} failed after {download_time:.2f}s")
            
            self.download_stats['total_downloads'] += 1
            return result
            
        except Exception as e:
            logger.error(f"Download {task_id} error: {e}")
            self.download_stats['failed_downloads'] += 1
            self.download_stats['total_downloads'] += 1
            return None
    
    def _download_file_sync(self, url: str, task_id: str) -> Optional[Dict[str, Any]]:
        """Synchronous file download (runs in thread pool)."""
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        headers = {
            'User-Agent': self.user_agent,
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }
        
        # Create session with retry strategy
        session = requests.Session()
        retry_strategy = Retry(
            total=self.retry_attempts,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        try:
            response = session.get(
                url, 
                headers=headers, 
                allow_redirects=True,
                timeout=self.download_timeout,
                stream=True
            )
            
            if response.status_code != 200:
                logger.warning(f"HTTP {response.status_code} for {url}")
                return None
            
            # Check content length
            content_length = response.headers.get('Content-Length')
            if content_length:
                size = int(content_length)
                if size < self.min_size_bytes:
                    logger.warning(f"File too small: {size} bytes < {self.min_size_bytes} bytes")
                    return None
                if size > self.max_size_bytes:
                    logger.warning(f"File too large: {size} bytes > {self.max_size_bytes} bytes")
                    return None
            
            # Download content
            content = BytesIO()
            downloaded = 0
            
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    content.write(chunk)
                    downloaded += len(chunk)
                    
                    # Check size during download
                    if downloaded > self.max_size_bytes:
                        logger.warning(f"File too large during download: {downloaded} bytes")
                        return None
            
            if downloaded < self.min_size_bytes:
                logger.warning(f"File too small: {downloaded} bytes < {self.min_size_bytes} bytes")
                return None
            
            # Validate file type
            content.seek(0)
            file_data = content.read()
            content.seek(0)
            
            # Detect MIME type
            mime_type = magic.from_buffer(file_data, mime=True)
            extension = self._get_extension_from_mime(mime_type)
            
            if not extension:
                logger.warning(f"Unsupported file type: {mime_type}")
                return None
            
            # Generate filename
            filename = self._generate_filename(url, extension, task_id)
            
            return {
                'data': content,
                'filename': filename,
                'size': downloaded,
                'extension': extension,
                'mime_type': mime_type
            }
            
        except Exception as e:
            logger.error(f"Download error for {url}: {e}")
            return None
        finally:
            session.close()
    
    def _get_extension_from_mime(self, mime_type: str) -> Optional[str]:
        """Get file extension from MIME type."""
        for ext, mimes in self.VALID_EXTENSIONS.items():
            if mime_type in mimes:
                return ext
        return None
    
    def _generate_filename(self, url: str, extension: str, task_id: str) -> str:
        """Generate filename from URL and extension."""
        try:
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)
            if not filename or '.' not in filename:
                filename = f"book_{task_id}.{extension}"
            else:
                name, _ = os.path.splitext(filename)
                filename = f"{name}.{extension}"
            
            # Clean filename
            filename = re.sub(r'[^\w\-_\.]', '_', filename)
            return filename
            
        except Exception:
            return f"book_{task_id}.{extension}"
    
    def _get_link_priority(self, link: Dict[str, str]) -> int:
        """Get priority for link sorting (lower = higher priority)."""
        url = link.get('url', '').lower()
        
        # Direct download links get highest priority
        if any(domain in url for domain in ['cdn3.booksdl.lc', 'libgen.la', 'libgen.li']):
            return 1
        
        # Other direct links
        if 'get.php' in url or 'download' in url:
            return 2
        
        # Everything else
        return 3
    
    def get_stats(self) -> Dict[str, Any]:
        """Get download statistics."""
        return self.download_stats.copy()
