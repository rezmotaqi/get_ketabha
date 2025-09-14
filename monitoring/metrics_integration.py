#!/usr/bin/env python3
"""
Metrics integration for the Telegram LibGen Bot.
Integrates Prometheus metrics with existing application components.
"""

import time
import asyncio
import psutil
import logging
from typing import Dict, Any, Optional
from functools import wraps

from .prometheus_metrics import get_metrics, track_request_lifecycle, track_async_request_lifecycle

logger = logging.getLogger(__name__)

class MetricsIntegration:
    """
    Integrates Prometheus metrics with the application components.
    """
    
    def __init__(self):
        self.metrics = get_metrics()
        self.start_time = time.time()
        self._update_system_metrics_task = None
    
    def start_system_metrics_updates(self):
        """Start periodic system metrics updates."""
        if self._update_system_metrics_task is None:
            try:
                loop = asyncio.get_event_loop()
                self._update_system_metrics_task = loop.create_task(self._update_system_metrics_loop())
            except RuntimeError:
                # No event loop running, start one
                import threading
                def run_loop():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    self._update_system_metrics_task = loop.create_task(self._update_system_metrics_loop())
                    loop.run_forever()
                
                thread = threading.Thread(target=run_loop, daemon=True)
                thread.start()
    
    async def _update_system_metrics_loop(self):
        """Update system metrics every 30 seconds."""
        while True:
            try:
                # Get system metrics
                memory_info = psutil.virtual_memory()
                cpu_percent = psutil.cpu_percent(interval=1)
                
                # Update Prometheus metrics
                self.metrics.update_system_metrics(
                    memory_bytes=memory_info.used,
                    cpu_percent=cpu_percent
                )
                
                # Update connection pool metrics (if available)
                try:
                    from .http_client import get_http_client
                    http_client = get_http_client()
                    if hasattr(http_client, '_pool'):
                        pool = http_client._pool
                        self.metrics.update_connection_pool_metrics(
                            total_size=pool.size,
                            available=pool.size - len(pool._pool)
                        )
                except Exception as e:
                    logger.debug(f"Could not update connection pool metrics: {e}")
                
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Error updating system metrics: {e}")
                await asyncio.sleep(30)
    
    def stop_system_metrics_updates(self):
        """Stop system metrics updates."""
        if self._update_system_metrics_task:
            self._update_system_metrics_task.cancel()
            self._update_system_metrics_task = None
    
    def record_system_status(self, component: str, status: str):
        """Record system status metrics."""
        self.metrics.record_system_status(component, status)
    
    def update_system_uptime(self, uptime_seconds: float):
        """Update system uptime."""
        self.metrics.update_system_uptime(uptime_seconds)
    
    def record_request_content(self, method: str, endpoint: str, content_size: int, headers_count: int):
        """Record request content metrics."""
        self.metrics.record_request_content(method, endpoint, content_size, headers_count)
    
    def record_response_content(self, method: str, endpoint: str, status: str, content_size: int, headers_count: int):
        """Record response content metrics."""
        self.metrics.record_response_content(method, endpoint, status, content_size, headers_count)
    
    def record_user_info(self, user_id: str, username: str, user_type: str, action: str):
        """Record user information metrics."""
        self.metrics.record_user_info(user_id, username, user_type, action)
    
    def record_user_activity_detailed(self, user_id: str, username: str, activity_type: str, query: str):
        """Record detailed user activity metrics."""
        self.metrics.record_user_activity_detailed(user_id, username, activity_type, query)
    
    def record_user_query_length(self, user_id: str, username: str, query_length: int):
        """Record user query length metrics."""
        self.metrics.record_user_query_length(user_id, username, query_length)
    
    def record_user_response_time(self, user_id: str, username: str, query_type: str, response_time: float):
        """Record user response time metrics."""
        self.metrics.record_user_response_time(user_id, username, query_type, response_time)

# Global metrics integration instance
_metrics_integration: Optional[MetricsIntegration] = None

def get_metrics_integration() -> MetricsIntegration:
    """Get the global metrics integration instance."""
    global _metrics_integration
    if _metrics_integration is None:
        _metrics_integration = MetricsIntegration()
    return _metrics_integration

def track_search_request(query: str, max_results: int = 10):
    """Decorator to track search requests."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            results_count = 0
            
            try:
                result = await func(*args, **kwargs)
                results_count = len(result) if result else 0
                return result
            except Exception as e:
                status = "error"
                logger.error(f"Search request failed: {e}")
                raise
            finally:
                duration = time.time() - start_time
                metrics = get_metrics()
                metrics.record_search_request("book_search", status, duration, results_count)
                
                # Record request stages
                metrics.record_request_stage("search_processing", "search", duration)
        
        return wrapper
    return decorator

def track_download_request(file_type: str = "unknown"):
    """Decorator to track download requests."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            size_bytes = 0
            speed_bytes_per_second = 0
            
            try:
                result = await func(*args, **kwargs)
                if result and isinstance(result, dict):
                    size_bytes = result.get('size', 0)
                return result
            except Exception as e:
                status = "error"
                logger.error(f"Download request failed: {e}")
                raise
            finally:
                duration = time.time() - start_time
                if size_bytes > 0 and duration > 0:
                    speed_bytes_per_second = size_bytes / duration
                
                metrics = get_metrics()
                metrics.record_download_request(file_type, status, duration, size_bytes, speed_bytes_per_second)
                
                # Record request stages
                metrics.record_request_stage("download_processing", "download", duration)
        
        return wrapper
    return decorator

def track_bot_message(message_type: str):
    """Decorator to track bot messages."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            status = "success"
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                logger.error(f"Bot message processing failed: {e}")
                raise
            finally:
                metrics = get_metrics()
                metrics.record_bot_message(message_type, status)
        
        return wrapper
    return decorator

def track_bot_command(command: str):
    """Decorator to track bot commands."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            status = "success"
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                logger.error(f"Bot command processing failed: {e}")
                raise
            finally:
                metrics = get_metrics()
                metrics.record_bot_command(command, status)
        
        return wrapper
    return decorator

def track_cache_operation(cache_type: str):
    """Decorator to track cache operations."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            hit = False
            
            try:
                result = func(*args, **kwargs)
                hit = result is not None
                return result
            except Exception as e:
                logger.error(f"Cache operation failed: {e}")
                raise
            finally:
                metrics = get_metrics()
                metrics.record_cache_request(cache_type, hit)
        
        return wrapper
    return decorator

def track_mirror_request(mirror_name: str):
    """Decorator to track mirror requests."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                logger.error(f"Mirror request failed: {e}")
                raise
            finally:
                duration = time.time() - start_time
                metrics = get_metrics()
                metrics.record_mirror_request(mirror_name, status, duration)
        
        return wrapper
    return decorator

def track_file_processing(file_type: str, operation: str):
    """Decorator to track file processing operations."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                logger.error(f"File processing failed: {e}")
                # Record error
                metrics = get_metrics()
                metrics.record_file_processing_error(file_type, type(e).__name__)
                raise
            finally:
                duration = time.time() - start_time
                metrics = get_metrics()
                metrics.record_file_processing(file_type, operation, duration)
        
        return wrapper
    return decorator

class RequestLifecycleTracker:
    """
    Tracks the complete lifecycle of a request through all stages.
    """
    
    def __init__(self, request_id: str, endpoint: str = "unknown"):
        self.request_id = request_id
        self.endpoint = endpoint
        self.start_time = time.time()
        self.stages = {}
        self.metrics = get_metrics()
    
    def start_stage(self, stage_name: str):
        """Start tracking a request stage."""
        self.stages[stage_name] = {
            'start_time': time.time(),
            'duration': None
        }
        logger.debug(f"Request {self.request_id}: Started stage '{stage_name}'")
    
    def end_stage(self, stage_name: str):
        """End tracking a request stage."""
        if stage_name in self.stages:
            stage = self.stages[stage_name]
            stage['duration'] = time.time() - stage['start_time']
            
            # Record in Prometheus
            self.metrics.record_request_stage(stage_name, self.endpoint, stage['duration'])
            
            logger.debug(f"Request {self.request_id}: Completed stage '{stage_name}' in {stage['duration']:.3f}s")
    
    def get_total_duration(self) -> float:
        """Get total request duration."""
        return time.time() - self.start_time
    
    def get_stage_summary(self) -> Dict[str, Any]:
        """Get summary of all stages."""
        summary = {
            'request_id': self.request_id,
            'endpoint': self.endpoint,
            'total_duration': self.get_total_duration(),
            'stages': {}
        }
        
        for stage_name, stage_data in self.stages.items():
            summary['stages'][stage_name] = {
                'duration': stage_data['duration'],
                'start_time': stage_data['start_time']
            }
        
        return summary

def create_request_tracker(request_id: str, endpoint: str = "unknown") -> RequestLifecycleTracker:
    """Create a new request lifecycle tracker."""
    return RequestLifecycleTracker(request_id, endpoint)

# Example usage functions
async def example_tracked_search(query: str, max_results: int = 10):
    """Example of a tracked search function."""
    
    @track_search_request(query, max_results)
    async def _search():
        # Simulate search processing
        await asyncio.sleep(0.5)
        return [{"title": f"Book {i}", "author": f"Author {i}"} for i in range(max_results)]
    
    return await _search()

async def example_tracked_download(file_url: str, file_type: str = "pdf"):
    """Example of a tracked download function."""
    
    @track_download_request(file_type)
    async def _download():
        # Simulate download processing
        await asyncio.sleep(1.0)
        return {
            "size": 1024 * 1024,  # 1MB
            "content": b"fake file content"
        }
    
    return await _download()

# Initialize metrics integration
def initialize_metrics(port: int = 8000):
    """Initialize the metrics system."""
    from .prometheus_metrics import start_metrics_server
    
    # Start metrics server
    start_metrics_server(port)
    
    # Start system metrics updates
    integration = get_metrics_integration()
    integration.start_system_metrics_updates()
    
    logger.info(f"Metrics system initialized on port {port}")

if __name__ == "__main__":
    # Example usage
    import asyncio
    
    async def main():
        # Initialize metrics
        initialize_metrics()
        
        # Example tracked operations
        await example_tracked_search("python programming", 5)
        await example_tracked_download("http://example.com/book.pdf", "pdf")
        
        # Example request lifecycle tracking
        tracker = create_request_tracker("req_123", "search")
        
        tracker.start_stage("validation")
        await asyncio.sleep(0.1)
        tracker.end_stage("validation")
        
        tracker.start_stage("search")
        await asyncio.sleep(0.5)
        tracker.end_stage("search")
        
        tracker.start_stage("formatting")
        await asyncio.sleep(0.2)
        tracker.end_stage("formatting")
        
        print("Request summary:", tracker.get_stage_summary())
    
    asyncio.run(main())
