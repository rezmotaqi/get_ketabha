#!/usr/bin/env python3
"""
Prometheus metrics integration for the Telegram LibGen Bot.
Provides comprehensive request lifecycle monitoring and performance metrics.
"""

import time
import functools
from typing import Dict, Any, Optional
from prometheus_client import (
    Counter, Histogram, Gauge, Summary, 
    start_http_server, generate_latest, 
    CollectorRegistry, CONTENT_TYPE_LATEST
)
from prometheus_client.core import REGISTRY
import logging

logger = logging.getLogger(__name__)

class PrometheusMetrics:
    """
    Prometheus metrics collector for comprehensive request lifecycle monitoring.
    """
    
    def __init__(self, port: int = 8000):
        self.port = port
        self.registry = CollectorRegistry()
        
        # Request metrics
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )
        
        self.http_request_duration_seconds = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry
        )
        
        # Search metrics
        self.search_requests_total = Counter(
            'search_requests_total',
            'Total search requests',
            ['query_type', 'status'],
            registry=self.registry
        )
        
        self.search_duration_seconds = Histogram(
            'search_duration_seconds',
            'Search request duration in seconds',
            ['query_type'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
            registry=self.registry
        )
        
        self.search_results_count = Histogram(
            'search_results_count',
            'Number of search results returned',
            ['query_type'],
            buckets=[0, 1, 5, 10, 25, 50, 100, 250, 500],
            registry=self.registry
        )
        
        # Download metrics
        self.download_requests_total = Counter(
            'download_requests_total',
            'Total download requests',
            ['file_type', 'status'],
            registry=self.registry
        )
        
        self.download_duration_seconds = Histogram(
            'download_duration_seconds',
            'Download duration in seconds',
            ['file_type'],
            buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
            registry=self.registry
        )
        
        self.download_size_bytes = Histogram(
            'download_size_bytes',
            'Download file size in bytes',
            ['file_type'],
            buckets=[1024, 10240, 102400, 1048576, 10485760, 104857600, 1073741824],
            registry=self.registry
        )
        
        self.download_speed_bytes_per_second = Histogram(
            'download_speed_bytes_per_second',
            'Download speed in bytes per second',
            ['file_type'],
            buckets=[1024, 10240, 102400, 1048576, 10485760, 104857600, 1073741824],
            registry=self.registry
        )
        
        # Cache metrics
        self.cache_requests_total = Counter(
            'cache_requests_total',
            'Total cache requests',
            ['cache_type', 'result'],
            registry=self.registry
        )
        
        self.cache_hits_total = Counter(
            'cache_hits_total',
            'Total cache hits',
            ['cache_type'],
            registry=self.registry
        )
        
        self.cache_size = Gauge(
            'cache_size',
            'Current cache size',
            ['cache_type'],
            registry=self.registry
        )
        
        # Bot metrics
        self.active_users = Gauge(
            'active_users',
            'Number of active users',
            registry=self.registry
        )
        
        self.bot_messages_total = Counter(
            'bot_messages_total',
            'Total bot messages processed',
            ['message_type', 'status'],
            registry=self.registry
        )
        
        # User activity metrics
        self.user_activity_total = Counter(
            'user_activity_total',
            'Total user activities',
            ['username', 'activity_type'],
            registry=self.registry
        )
        
        self.user_activity_duration_seconds = Histogram(
            'user_activity_duration_seconds',
            'User activity duration in seconds',
            ['username', 'activity_type'],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry
        )
        
        self.bot_commands_total = Counter(
            'bot_commands_total',
            'Total bot commands processed',
            ['command', 'status'],
            registry=self.registry
        )
        
        # Error metrics
        self.errors_total = Counter(
            'errors_total',
            'Total errors',
            ['error_type', 'component'],
            registry=self.registry
        )
        
        # Performance metrics
        self.memory_usage_bytes = Gauge(
            'memory_usage_bytes',
            'Memory usage in bytes',
            registry=self.registry
        )
        
        self.cpu_usage_percent = Gauge(
            'cpu_usage_percent',
            'CPU usage percentage',
            registry=self.registry
        )
        
        # Connection pool metrics
        self.connection_pool_size = Gauge(
            'connection_pool_size',
            'HTTP connection pool size',
            registry=self.registry
        )
        
        self.connection_pool_available = Gauge(
            'connection_pool_available',
            'Available connections in pool',
            registry=self.registry
        )
        
        # Request lifecycle stages
        self.request_stage_duration_seconds = Histogram(
            'request_stage_duration_seconds',
            'Request stage duration in seconds',
            ['stage', 'endpoint'],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
            registry=self.registry
        )
        
        # Mirror performance metrics
        self.mirror_response_time_seconds = Histogram(
            'mirror_response_time_seconds',
            'Mirror response time in seconds',
            ['mirror_name'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
            registry=self.registry
        )
        
        self.mirror_requests_total = Counter(
            'mirror_requests_total',
            'Total requests to mirrors',
            ['mirror_name', 'status'],
            registry=self.registry
        )
        
        # User session metrics
        self.user_sessions_total = Counter(
            'user_sessions_total',
            'Total user sessions',
            ['status'],
            registry=self.registry
        )
        
        self.user_session_duration_seconds = Histogram(
            'user_session_duration_seconds',
            'User session duration in seconds',
            buckets=[60, 300, 900, 1800, 3600, 7200, 14400],
            registry=self.registry
        )
        
        # File processing metrics
        self.file_processing_duration_seconds = Histogram(
            'file_processing_duration_seconds',
            'File processing duration in seconds',
            ['file_type', 'operation'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry
        )
        
        self.file_processing_errors_total = Counter(
            'file_processing_errors_total',
            'Total file processing errors',
            ['file_type', 'error_type'],
            registry=self.registry
        )
        
        # System status metrics
        self.system_status = Gauge(
            'system_status',
            'System status indicators',
            ['component', 'status'],
            registry=self.registry
        )
        
        self.system_uptime_seconds = Gauge(
            'system_uptime_seconds',
            'System uptime in seconds',
            registry=self.registry
        )
        
        # Request/Response content metrics
        self.request_content_size_bytes = Histogram(
            'request_content_size_bytes',
            'Request content size in bytes',
            ['method', 'endpoint'],
            buckets=[100, 500, 1000, 5000, 10000, 50000, 100000, 500000],
            registry=self.registry
        )
        
        self.response_content_size_bytes = Histogram(
            'response_content_size_bytes',
            'Response content size in bytes',
            ['method', 'endpoint', 'status'],
            buckets=[100, 500, 1000, 5000, 10000, 50000, 100000, 500000],
            registry=self.registry
        )
        
        self.request_headers_count = Histogram(
            'request_headers_count',
            'Number of request headers',
            ['method', 'endpoint'],
            buckets=[5, 10, 15, 20, 25, 30, 40, 50],
            registry=self.registry
        )
        
        self.response_headers_count = Histogram(
            'response_headers_count',
            'Number of response headers',
            ['method', 'endpoint', 'status'],
            buckets=[5, 10, 15, 20, 25, 30, 40, 50],
            registry=self.registry
        )
        
        # Enhanced user information metrics
        self.user_info_total = Counter(
            'user_info_total',
            'Total user information records',
            ['user_id', 'username', 'user_type', 'action'],
            registry=self.registry
        )
        
        self.user_activity_by_type = Counter(
            'user_activity_by_type',
            'User activity by type',
            ['user_id', 'username', 'activity_type', 'query'],
            registry=self.registry
        )
        
        self.user_query_length = Histogram(
            'user_query_length',
            'User query length in characters',
            ['user_id', 'username'],
            buckets=[10, 20, 50, 100, 200, 500, 1000],
            registry=self.registry
        )
        
        self.user_response_time = Histogram(
            'user_response_time',
            'User response time in seconds',
            ['user_id', 'username', 'query_type'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
            registry=self.registry
        )
    
    def start_server(self):
        """Start the Prometheus metrics server."""
        try:
            start_http_server(self.port, registry=self.registry)
            logger.info(f"Prometheus metrics server started on port {self.port}")
        except Exception as e:
            logger.error(f"Failed to start Prometheus metrics server: {e}")
    
    def get_metrics(self) -> str:
        """Get the current metrics in Prometheus format."""
        return generate_latest(self.registry)
    
    def record_http_request(self, method: str, endpoint: str, status: str, duration: float):
        """Record HTTP request metrics."""
        self.http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
        self.http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
    
    def record_search_request(self, query_type: str, status: str, duration: float, results_count: int):
        """Record search request metrics."""
        self.search_requests_total.labels(query_type=query_type, status=status).inc()
        self.search_duration_seconds.labels(query_type=query_type).observe(duration)
        self.search_results_count.labels(query_type=query_type).observe(results_count)
    
    def record_download_request(self, file_type: str, status: str, duration: float, 
                              size_bytes: int, speed_bytes_per_second: float):
        """Record download request metrics."""
        self.download_requests_total.labels(file_type=file_type, status=status).inc()
        self.download_duration_seconds.labels(file_type=file_type).observe(duration)
        self.download_size_bytes.labels(file_type=file_type).observe(size_bytes)
        self.download_speed_bytes_per_second.labels(file_type=file_type).observe(speed_bytes_per_second)
    
    def record_cache_request(self, cache_type: str, hit: bool):
        """Record cache request metrics."""
        result = 'hit' if hit else 'miss'
        self.cache_requests_total.labels(cache_type=cache_type, result=result).inc()
        if hit:
            self.cache_hits_total.labels(cache_type=cache_type).inc()
    
    def record_bot_message(self, message_type: str, status: str):
        """Record bot message metrics."""
        self.bot_messages_total.labels(message_type=message_type, status=status).inc()
    
    def record_user_activity(self, username: str, activity_type: str, duration: float):
        """Record user activity metrics."""
        self.user_activity_total.labels(username=username, activity_type=activity_type).inc()
        self.user_activity_duration_seconds.labels(username=username, activity_type=activity_type).observe(duration)
    
    def record_bot_command(self, command: str, status: str):
        """Record bot command metrics."""
        self.bot_commands_total.labels(command=command, status=status).inc()
    
    def record_error(self, error_type: str, component: str):
        """Record error metrics."""
        self.errors_total.labels(error_type=error_type, component=component).inc()
    
    def record_request_stage(self, stage: str, endpoint: str, duration: float):
        """Record request stage duration."""
        self.request_stage_duration_seconds.labels(stage=stage, endpoint=endpoint).observe(duration)
    
    def record_mirror_request(self, mirror_name: str, status: str, response_time: float):
        """Record mirror request metrics."""
        self.mirror_requests_total.labels(mirror_name=mirror_name, status=status).inc()
        self.mirror_response_time_seconds.labels(mirror_name=mirror_name).observe(response_time)
    
    def record_file_processing(self, file_type: str, operation: str, duration: float):
        """Record file processing metrics."""
        self.file_processing_duration_seconds.labels(file_type=file_type, operation=operation).observe(duration)
    
    def record_file_processing_error(self, file_type: str, error_type: str):
        """Record file processing error metrics."""
        self.file_processing_errors_total.labels(file_type=file_type, error_type=error_type).inc()
    
    def update_system_metrics(self, memory_bytes: int, cpu_percent: float):
        """Update system resource metrics."""
        self.memory_usage_bytes.set(memory_bytes)
        self.cpu_usage_percent.set(cpu_percent)
    
    def update_connection_pool_metrics(self, total_size: int, available: int):
        """Update connection pool metrics."""
        self.connection_pool_size.set(total_size)
        self.connection_pool_available.set(available)
    
    def update_cache_size(self, cache_type: str, size: int):
        """Update cache size metrics."""
        self.cache_size.labels(cache_type=cache_type).set(size)
    
    def update_active_users(self, count: int):
        """Update active users count."""
        self.active_users.set(count)
    
    def record_system_status(self, component: str, status: str):
        """Record system status metrics."""
        self.system_status.labels(component=component, status=status).set(1)
    
    def update_system_uptime(self, uptime_seconds: float):
        """Update system uptime."""
        self.system_uptime_seconds.set(uptime_seconds)
    
    def record_request_content(self, method: str, endpoint: str, content_size: int, headers_count: int):
        """Record request content metrics."""
        self.request_content_size_bytes.labels(method=method, endpoint=endpoint).observe(content_size)
        self.request_headers_count.labels(method=method, endpoint=endpoint).observe(headers_count)
    
    def record_response_content(self, method: str, endpoint: str, status: str, content_size: int, headers_count: int):
        """Record response content metrics."""
        self.response_content_size_bytes.labels(method=method, endpoint=endpoint, status=status).observe(content_size)
        self.response_headers_count.labels(method=method, endpoint=endpoint, status=status).observe(headers_count)
    
    def record_user_info(self, user_id: str, username: str, user_type: str, action: str):
        """Record user information metrics."""
        self.user_info_total.labels(user_id=user_id, username=username, user_type=user_type, action=action).inc()
    
    def record_user_activity_detailed(self, user_id: str, username: str, activity_type: str, query: str):
        """Record detailed user activity metrics."""
        self.user_activity_by_type.labels(user_id=user_id, username=username, activity_type=activity_type, query=query).inc()
    
    def record_user_query_length(self, user_id: str, username: str, query_length: int):
        """Record user query length metrics."""
        self.user_query_length.labels(user_id=user_id, username=username).observe(query_length)
    
    def record_user_response_time(self, user_id: str, username: str, query_type: str, response_time: float):
        """Record user response time metrics."""
        self.user_response_time.labels(user_id=user_id, username=username, query_type=query_type).observe(response_time)


# Global metrics instance
_metrics_instance: Optional[PrometheusMetrics] = None

def get_metrics() -> PrometheusMetrics:
    """Get the global metrics instance."""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = PrometheusMetrics()
    return _metrics_instance

def start_metrics_server(port: int = 8000):
    """Start the metrics server."""
    metrics = get_metrics()
    metrics.port = port
    metrics.start_server()

def track_request_lifecycle(stage: str, endpoint: str = "unknown"):
    """Decorator to track request lifecycle stages."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                get_metrics().record_request_stage(stage, endpoint, duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                get_metrics().record_request_stage(stage, endpoint, duration)
                get_metrics().record_error(type(e).__name__, stage)
                raise
        return wrapper
    return decorator

def track_async_request_lifecycle(stage: str, endpoint: str = "unknown"):
    """Decorator to track async request lifecycle stages."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                get_metrics().record_request_stage(stage, endpoint, duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                get_metrics().record_request_stage(stage, endpoint, duration)
                get_metrics().record_error(type(e).__name__, stage)
                raise
        return wrapper
    return decorator
