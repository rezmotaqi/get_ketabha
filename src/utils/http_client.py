"""
Optimized HTTP Client Configuration
Provides high-performance HTTP clients with connection pooling and optimizations
"""

import asyncio
import aiohttp
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib3.poolmanager import PoolManager
import ssl
import time
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class OptimizedHTTPClient:
    """High-performance HTTP client with connection pooling and optimizations"""
    
    def __init__(self, 
                 max_connections: int = 100,
                 max_keepalive_connections: int = 20,
                 keepalive_timeout: int = 30,
                 connect_timeout: int = 10,
                 read_timeout: int = 30,
                 retry_attempts: int = 3,
                 backoff_factor: float = 0.3):
        """
        Initialize optimized HTTP client
        
        Args:
            max_connections: Maximum number of connections in the pool
            max_keepalive_connections: Maximum number of keep-alive connections
            keepalive_timeout: Keep-alive timeout in seconds
            connect_timeout: Connection timeout in seconds
            read_timeout: Read timeout in seconds
            retry_attempts: Number of retry attempts
            backoff_factor: Backoff factor for retries
        """
        self.max_connections = max_connections
        self.max_keepalive_connections = max_keepalive_connections
        self.keepalive_timeout = keepalive_timeout
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.retry_attempts = retry_attempts
        self.backoff_factor = backoff_factor
        
        # Create optimized session
        self.session = self._create_optimized_session()
        self._aio_session: Optional[aiohttp.ClientSession] = None
        
    def _create_optimized_session(self) -> requests.Session:
        """Create an optimized requests session with connection pooling"""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.retry_attempts,
            backoff_factor=self.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        
        # Create HTTP adapter with optimizations
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=self.max_connections,
            pool_maxsize=self.max_keepalive_connections,
            pool_block=False
        )
        
        # Mount adapters
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Configure SSL context
        ssl_context = ssl.create_default_context()
        ssl_context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
        
        # Set timeouts
        session.timeout = (self.connect_timeout, self.read_timeout)
        
        return session
    
    async def get_aio_session(self) -> aiohttp.ClientSession:
        """Get or create async HTTP session"""
        if self._aio_session is None or self._aio_session.closed:
            # Configure connector with optimizations
            connector = aiohttp.TCPConnector(
                limit=self.max_connections,
                limit_per_host=self.max_keepalive_connections,
                keepalive_timeout=self.keepalive_timeout,
                enable_cleanup_closed=True,
                ttl_dns_cache=300,  # 5 minutes DNS cache
                use_dns_cache=True,
                family=0,  # Use both IPv4 and IPv6
                ssl=False,  # We'll handle SSL in timeout
            )
            
            # Configure timeout
            timeout = aiohttp.ClientTimeout(
                total=self.read_timeout,
                connect=self.connect_timeout,
                sock_read=self.read_timeout
            )
            
            # Create session with optimizations
            self._aio_session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                },
                raise_for_status=False,
                auto_decompress=True,
                read_bufsize=65536,  # 64KB read buffer
            )
        
        return self._aio_session
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """Optimized GET request"""
        return self.session.get(url, **kwargs)
    
    def post(self, url: str, **kwargs) -> requests.Response:
        """Optimized POST request"""
        return self.session.post(url, **kwargs)
    
    async def aio_get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Async GET request"""
        session = await self.get_aio_session()
        return await session.get(url, **kwargs)
    
    async def aio_post(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Async POST request"""
        session = await self.get_aio_session()
        return await session.post(url, **kwargs)
    
    def stream_download(self, url: str, chunk_size: int = 8192, **kwargs):
        """Stream download with optimized chunk size"""
        response = self.session.get(url, stream=True, **kwargs)
        response.raise_for_status()
        
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                yield chunk
    
    async def aio_stream_download(self, url: str, chunk_size: int = 8192, **kwargs):
        """Async stream download with optimized chunk size"""
        session = await self.get_aio_session()
        async with session.get(url, **kwargs) as response:
            response.raise_for_status()
            
            async for chunk in response.content.iter_chunked(chunk_size):
                if chunk:
                    yield chunk
    
    def close(self):
        """Close the session and cleanup resources"""
        if self.session:
            self.session.close()
        
        if self._aio_session and not self._aio_session.closed:
            asyncio.create_task(self._aio_session.close())
    
    async def aclose(self):
        """Async close the session"""
        if self._aio_session and not self._aio_session.closed:
            await self._aio_session.close()

# Global optimized client instance
_http_client: Optional[OptimizedHTTPClient] = None

def get_http_client() -> OptimizedHTTPClient:
    """Get the global optimized HTTP client instance"""
    global _http_client
    if _http_client is None:
        _http_client = OptimizedHTTPClient()
    return _http_client

def close_http_client():
    """Close the global HTTP client"""
    global _http_client
    if _http_client:
        _http_client.close()
        _http_client = None

# Performance monitoring
class PerformanceMonitor:
    """Monitor HTTP performance metrics"""
    
    def __init__(self):
        self.request_times: Dict[str, float] = {}
        self.request_counts: Dict[str, int] = {}
        self.total_bytes: Dict[str, int] = {}
    
    def record_request(self, url: str, duration: float, bytes_transferred: int = 0):
        """Record request performance metrics"""
        domain = url.split('/')[2] if '://' in url else 'unknown'
        
        if domain not in self.request_times:
            self.request_times[domain] = 0
            self.request_counts[domain] = 0
            self.total_bytes[domain] = 0
        
        self.request_times[domain] += duration
        self.request_counts[domain] += 1
        self.total_bytes[domain] += bytes_transferred
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        stats = {}
        for domain in self.request_times:
            avg_time = self.request_times[domain] / self.request_counts[domain]
            avg_speed = (self.total_bytes[domain] * 8) / (self.request_times[domain] * 1_000_000) if self.request_times[domain] > 0 else 0
            
            stats[domain] = {
                'total_requests': self.request_counts[domain],
                'total_time': self.request_times[domain],
                'average_time': avg_time,
                'total_bytes': self.total_bytes[domain],
                'average_speed_mbps': avg_speed
            }
        
        return stats

# Global performance monitor
_performance_monitor = PerformanceMonitor()

def get_performance_stats() -> Dict[str, Any]:
    """Get current performance statistics"""
    return _performance_monitor.get_stats()

def record_request_performance(url: str, duration: float, bytes_transferred: int = 0):
    """Record request performance"""
    _performance_monitor.record_request(url, duration, bytes_transferred)
