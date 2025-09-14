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
