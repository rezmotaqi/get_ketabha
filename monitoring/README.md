# Monitoring Module

This directory contains all monitoring and metrics-related files for the Telegram LibGen Bot.

## Files

### Core Files
- **`prometheus.yml`** - Prometheus configuration file
- **`prometheus_metrics.py`** - Core Prometheus metrics implementation
- **`metrics_integration.py`** - Integration utilities and decorators
- **`setup_monitoring.sh`** - Setup script for monitoring infrastructure

### Configuration
- **`__init__.py`** - Module initialization and exports

## Usage

### Basic Setup
```bash
# Run the setup script
./monitoring/setup_monitoring.sh

# Start metrics server
python -c "from monitoring import initialize_metrics; initialize_metrics()"
```

### Using Metrics in Code
```python
from monitoring import (
    track_search_request,
    track_download_request,
    create_request_tracker
)

# Track search requests
@track_search_request("book_search")
async def search_books(query):
    # Your search logic here
    pass

# Track request lifecycle
tracker = create_request_tracker("req_123", "search")
tracker.start_stage("validation")
# ... do work ...
tracker.end_stage("validation")
```

### Prometheus Queries
Access metrics at: `http://localhost:8000/metrics`

Key metrics:
- `search_requests_total` - Total search requests
- `search_duration_seconds` - Search duration histogram
- `active_users` - Number of active users
- `errors_total` - Error counts by type

## Dashboard Access

### Prometheus UI
**URL:** http://localhost:9090

**Key Queries:**
```promql
# Search requests by status
search_requests_total{status="success"}
search_requests_total{status="started"}

# User activity
user_activity_by_type_total

# System metrics
memory_usage_bytes
cpu_usage_percent
system_status

# Search performance
search_duration_seconds
search_results_count

# Bot health
up{job="libgen-bot"}
```

**Navigation:**
- **Graph** - Query and visualize metrics
- **Status → Targets** - Check bot connectivity
- **Status → Rules** - View alerting rules
- **Alerts** - View active alerts

### Grafana Dashboard
**URL:** http://localhost:3000
**Login:** admin / admin123

**Pre-configured Dashboards:**
- **Telegram Bot Monitoring** - Main bot dashboard
- **System Overview** - Server resources
- **Search Analytics** - Search performance metrics
- **User Activity** - User behavior analytics

**Key Panels:**
- Active Users Count
- Search Requests Rate
- Average Search Duration
- Error Rates
- Memory/CPU Usage
- Response Time Percentiles

### Task Dashboard
**URL:** http://localhost:5000
**Purpose:** Task management and monitoring

### Quick Access Commands
```bash
# Check if services are running
curl http://localhost:8000/metrics | head -10
curl http://localhost:9090/api/v1/targets
curl http://localhost:3000/api/health

# Test specific metrics
curl "http://localhost:9090/api/v1/query?query=search_requests_total"
curl "http://localhost:9090/api/v1/query?query=up{job=\"libgen-bot\"}"
```

## Architecture

```
monitoring/
├── prometheus.yml          # Prometheus config
├── prometheus_metrics.py   # Core metrics class
├── metrics_integration.py  # Integration utilities
├── setup_monitoring.sh     # Setup script
├── __init__.py            # Module exports
└── README.md              # This file
```

## Integration

The monitoring module integrates with:
- **Prometheus** - Metrics collection and storage
- **Grafana** - Metrics visualization (via setup script)
- **Bot components** - Automatic metrics collection via decorators
- **System resources** - CPU, memory, and connection pool monitoring
