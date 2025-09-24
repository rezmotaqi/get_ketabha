#!/usr/bin/env python3
"""
File handling utilities for downloading and validating book files.
Handles file download, validation, and preparation for Telegram sending.
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

from .logger import setup_logger

logger = setup_logger(__name__)

class FileHandler:
    """Handles file downloading, validation, and preparation for Telegram."""
    
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
    
    # File size limits (in bytes)
    MIN_SIZE_BYTES = 1024 * 1024  # 1MB minimum
    MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50MB maximum
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize file handler with configuration."""
        self.config = config
        self.min_size_mb = float(config.get('FILE_MIN_SIZE_MB', 0.1))
        self.max_size_mb = float(config.get('FILE_MAX_SIZE_MB', 50))
        self.validation_timeout = int(config.get('FILE_VALIDATION_TIMEOUT', 30))
        self.download_timeout = int(config.get('FILE_DOWNLOAD_TIMEOUT', 60))
        self.retry_attempts = int(config.get('FILE_RETRY_ATTEMPTS', 2))
        self.user_agent = config.get('HTTP_USER_AGENT', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36')
        
        # Convert MB to bytes
        self.min_size_bytes = int(self.min_size_mb * 1024 * 1024)
        self.max_size_bytes = int(self.max_size_mb * 1024 * 1024)
        
        logger.debug(f"FileHandler initialized: min_size={self.min_size_mb}MB, max_size={self.max_size_mb}MB")
    
    async def download_and_validate_file(self, url: str, expected_filename: str = None) -> Optional[Dict[str, Any]]:
        """
        Download and validate a file from URL.
        
        Args:
            url: Download URL
            expected_filename: Expected filename for validation
            
        Returns:
            Dictionary with file data and metadata, or None if validation fails
        """
        try:
            logger.debug(f"Downloading file from: {url}")
            
            # Download file with validation
            file_data = await self._download_file(url)
            if not file_data:
                return None
            
            # Validate file
            validation_result = await self._validate_file(file_data, expected_filename)
            if not validation_result['valid']:
                logger.debug(f"File validation failed: {validation_result['reason']}")
                return None
            
            # Prepare file for Telegram
            return {
                'data': file_data['content'],
                'filename': validation_result['filename'],
                'mime_type': validation_result['mime_type'],
                'size': validation_result['size'],
                'extension': validation_result['extension'],
                'url': url
            }
            
        except Exception as e:
            logger.error(f"Error downloading/validating file from {url}: {str(e)}")
            return None
    
    async def _download_file(self, url: str) -> Optional[Dict[str, Any]]:
        """Download file from URL with retry logic."""
        headers = {
            'User-Agent': self.user_agent,
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }
        
        # Use more granular timeouts for large files
        timeout = aiohttp.ClientTimeout(
            total=self.download_timeout * 3,  # Total time: 3x configured timeout
            sock_read=30,                     # 30 seconds between chunks
            sock_connect=10                   # 10 seconds to establish connection
        )
        
        for attempt in range(self.retry_attempts):
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, headers=headers, allow_redirects=True) as response:
                        if response.status != 200:
                            logger.debug(f"HTTP {response.status} for {url} (attempt {attempt + 1})")
                            if attempt < self.retry_attempts - 1:
                                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                                continue
                            return None
                        
                        # Check content length
                        content_length = response.headers.get('Content-Length')
                        if content_length:
                            size = int(content_length)
                            if size < self.min_size_bytes:
                                logger.debug(f"File too small: {size} bytes < {self.min_size_bytes} bytes")
                                return None
                            if size > self.max_size_bytes:
                                logger.debug(f"File too large: {size} bytes > {self.max_size_bytes} bytes")
                                return None
                        
                        # Download content with percentage display
                        content = BytesIO()
                        downloaded = 0
                        
                        # Get total size for percentage calculation
                        content_length = response.headers.get('Content-Length')
                        total_size = int(content_length) if content_length else None
                        
                        # Track percentage reporting
                        last_reported_percent = -1
                        
                        async for chunk in response.content.iter_chunked(8192):
                            if not chunk:
                                continue
                            content.write(chunk)
                            downloaded += len(chunk)
                            
                            # Show percentage progress (more frequent for large files)
                            if total_size:
                                current_percent = int((downloaded / total_size) * 100)
                                if current_percent != last_reported_percent and current_percent % 5 == 0:
                                    size_mb = downloaded / (1024 * 1024)
                                    total_mb = total_size / (1024 * 1024)
                                    print(f"📊 Download progress: {current_percent}% ({size_mb:.1f}MB / {total_mb:.1f}MB)")
                                    last_reported_percent = current_percent
                            else:
                                # If no total size, show downloaded amount every 2MB
                                if downloaded % (2 * 1024 * 1024) == 0:
                                    size_mb = downloaded / (1024 * 1024)
                                    print(f"📊 Downloaded: {size_mb:.1f}MB")
                            
                            # Check size during download
                            if downloaded > self.max_size_bytes:
                                logger.debug(f"File exceeded size limit during download: {downloaded} bytes")
                                return None
                        
                        content.seek(0)
                        
                        return {
                            'content': content,
                            'size': downloaded,
                            'mime_type': response.headers.get('Content-Type', ''),
                            'filename': self._extract_filename_from_url(url, response.headers)
                        }
                        
            except asyncio.TimeoutError:
                logger.debug(f"Timeout downloading {url} (attempt {attempt + 1})")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
            except aiohttp.ClientError as e:
                logger.warning(f"Connection error downloading {url} (attempt {attempt + 1}): {str(e)}")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
            except Exception as e:
                logger.debug(f"Error downloading {url} (attempt {attempt + 1}): {str(e)}")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
        
        return None
    
    async def _validate_file(self, file_data: Dict[str, Any], expected_filename: str = None) -> Dict[str, Any]:
        """Validate downloaded file."""
        try:
            content = file_data['content']
            size = file_data['size']
            mime_type = file_data['mime_type']
            url_filename = file_data['filename']
            
            # Size validation
            if size < self.min_size_bytes:
                return {
                    'valid': False,
                    'reason': f'File too small: {size} bytes < {self.min_size_bytes} bytes'
                }
            
            if size > self.max_size_bytes:
                return {
                    'valid': False,
                    'reason': f'File too large: {size} bytes > {self.max_size_bytes} bytes'
                }
            
            # Read first few bytes for magic number detection
            content.seek(0)
            header = content.read(1024)
            content.seek(0)
            
            # Detect file type using python-magic
            try:
                detected_mime = magic.from_buffer(header, mime=True)
                logger.debug(f"Detected MIME type: {detected_mime}")
            except Exception:
                detected_mime = mime_type
                logger.debug(f"Could not detect MIME type, using: {detected_mime}")
            
            # Determine file extension
            extension = self._get_extension_from_mime(detected_mime, url_filename, expected_filename)
            if not extension:
                return {
                    'valid': False,
                    'reason': f'Unsupported file type: {detected_mime}'
                }
            
            # Validate extension is in our supported list
            if extension not in self.VALID_EXTENSIONS:
                return {
                    'valid': False,
                    'reason': f'Unsupported file extension: {extension}'
                }
            
            # Basic corruption check (file should not be empty or too small)
            if size < 1024:  # Less than 1KB is suspicious for a book
                return {
                    'valid': False,
                    'reason': f'File too small to be a valid book: {size} bytes'
                }
            
            # Generate proper filename
            filename = self._generate_filename(url_filename, expected_filename, extension)
            
            return {
                'valid': True,
                'filename': filename,
                'mime_type': detected_mime,
                'size': size,
                'extension': extension
            }
            
        except Exception as e:
            logger.error(f"Error validating file: {str(e)}")
            return {
                'valid': False,
                'reason': f'Validation error: {str(e)}'
            }
    
    def _extract_filename_from_url(self, url: str, headers: Dict[str, str]) -> str:
        """Extract filename from URL and headers."""
        # Try Content-Disposition header first
        content_disposition = headers.get('Content-Disposition', '')
        if content_disposition:
            filename_match = re.search(r'filename[*]?=(?:UTF-8\'\')?([^;]+)', content_disposition, re.IGNORECASE)
            if filename_match:
                try:
                    filename = unquote(filename_match.group(1).strip('"'))
                    if filename and '.' in filename:
                        return filename
                except Exception:
                    pass
        
        # Try URL path
        try:
            parsed_url = urlparse(url)
            path = parsed_url.path
            if path:
                filename = os.path.basename(path)
                if filename and '.' in filename:
                    return unquote(filename)
        except Exception:
            pass
        
        return 'book'
    
    def _get_extension_from_mime(self, mime_type: str, url_filename: str, expected_filename: str) -> Optional[str]:
        """Determine file extension from MIME type and filenames."""
        if not mime_type:
            mime_type = ''
        
        # Check MIME type against our valid extensions
        for ext, valid_mimes in self.VALID_EXTENSIONS.items():
            if mime_type.lower() in [m.lower() for m in valid_mimes]:
                return ext
        
        # Try to get extension from filename
        for filename in [url_filename, expected_filename]:
            if filename and '.' in filename:
                ext = filename.split('.')[-1].lower()
                if ext in self.VALID_EXTENSIONS:
                    return ext
        
        # Fallback to mimetypes module
        try:
            ext = mimetypes.guess_extension(mime_type)
            if ext and ext[1:] in self.VALID_EXTENSIONS:  # Remove the dot
                return ext[1:]
        except Exception:
            pass
        
        return None
    
    def _generate_filename(self, url_filename: str, expected_filename: str, extension: str) -> str:
        """Generate a proper filename for the file."""
        # Use expected filename if available and has extension
        if expected_filename and '.' in expected_filename:
            base_name = expected_filename.rsplit('.', 1)[0]
            return f"{base_name}.{extension}"
        
        # Use URL filename if available
        if url_filename and url_filename != 'book':
            base_name = url_filename.rsplit('.', 1)[0] if '.' in url_filename else url_filename
            return f"{base_name}.{extension}"
        
        # Generate default filename
        return f"book.{extension}"
    
    async def get_best_file_from_links(self, download_links: List[Dict[str, str]], book_title: str = None) -> Optional[Dict[str, Any]]:
        """
        Try to download and validate files from multiple download links.
        Returns the best valid file found.
        
        Args:
            download_links: List of download link dictionaries
            book_title: Book title for filename generation
            
        Returns:
            Best valid file data or None
        """
        if not download_links:
            return None
        
        # Sort links by priority (direct downloads first)
        sorted_links = sorted(download_links, key=lambda x: self._get_link_priority(x))
        
        logger.info(f"Trying to download file from {len(sorted_links)} links")
        print(f"📥 Starting download process for {len(sorted_links)} available links...")
        
        for i, link in enumerate(sorted_links):
            try:
                url = link.get('url', '')
                if not url:
                    continue
                
                logger.info(f"Attempting download {i+1}/{len(sorted_links)}: {url}")
                print(f"🔗 Attempting download {i+1}/{len(sorted_links)}: {url[:80]}...")
                
                # Generate expected filename
                expected_filename = None
                if book_title:
                    # Clean title for filename
                    clean_title = re.sub(r'[^\w\s-]', '', book_title)
                    clean_title = re.sub(r'[-\s]+', '_', clean_title)
                    expected_filename = clean_title[:50]  # Limit length
                
                # Download and validate
                file_data = await self.download_and_validate_file(url, expected_filename)
                if file_data:
                    logger.info(f"Successfully downloaded and validated file: {file_data['filename']}")
                    print(f"✅ Successfully downloaded: {file_data['filename']} ({file_data['size']} bytes)")
                    return file_data
                else:
                    logger.debug(f"Failed to download/validate file from: {url}")
                    
            except Exception as e:
                logger.debug(f"Error processing link {url}: {str(e)}")
                continue
        
        logger.debug("No valid files found from any download links")
        return None
    
    def _get_link_priority(self, link: Dict[str, str]) -> int:
        """Get priority score for a download link (lower is better)."""
        link_type = link.get('type', '')
        
        # Priority order: direct downloads first, then mirrors
        priority_map = {
            'direct_download': 1,
            'direct_mirror': 2,
            'libgen_direct': 3,
            'library_lol': 4,
            'annas_archive': 5,
            'z_library': 6,
            'ocean_pdf': 7,
            'liber3': 8,
            'memory_world': 9,
            'cyberleninka': 10,
        }
        
        return priority_map.get(link_type, 99)  # Unknown types get lowest priority


# Example usage and testing
async def test_file_handler():
    """Test function for file handler."""
    config = {
        'FILE_MIN_SIZE_MB': 0.1,
        'FILE_MAX_SIZE_MB': 50,
        'FILE_VALIDATION_TIMEOUT': 30,
        'FILE_DOWNLOAD_TIMEOUT': 60,
        'FILE_RETRY_ATTEMPTS': 2,
        'HTTP_USER_AGENT': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
    }
    
    handler = FileHandler(config)
    
    # Test with a sample URL
    test_url = "https://example.com/test.pdf"
    result = await handler.download_and_validate_file(test_url)
    
    if result:
        print(f"File downloaded successfully: {result['filename']}")
        print(f"Size: {result['size']} bytes")
        print(f"MIME type: {result['mime_type']}")
    else:
        print("Failed to download or validate file")


if __name__ == "__main__":
    asyncio.run(test_file_handler())
