#!/usr/bin/env python3
"""
Monitoring module for the Telegram LibGen Bot.
Provides Prometheus metrics, monitoring utilities, and system integration.
"""

from .prometheus_metrics import (
    PrometheusMetrics,
    get_metrics,
    start_metrics_server,
    track_request_lifecycle,
    track_async_request_lifecycle
)

from .metrics_integration import (
    MetricsIntegration,
    get_metrics_integration,
    track_search_request,
    track_download_request,
    track_bot_message,
    track_bot_command,
    track_cache_operation,
    track_mirror_request,
    track_file_processing,
    RequestLifecycleTracker,
    create_request_tracker,
    initialize_metrics
)

__all__ = [
    # Prometheus metrics
    'PrometheusMetrics',
    'get_metrics',
    'start_metrics_server',
    'track_request_lifecycle',
    'track_async_request_lifecycle',
    
    # Metrics integration
    'MetricsIntegration',
    'get_metrics_integration',
    'track_search_request',
    'track_download_request',
    'track_bot_message',
    'track_bot_command',
    'track_cache_operation',
    'track_mirror_request',
    'track_file_processing',
    'RequestLifecycleTracker',
    'create_request_tracker',
    'initialize_metrics'
]
