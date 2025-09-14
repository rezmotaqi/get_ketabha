#!/bin/bash

echo "🚀 Setting up Telegram Bot Monitoring System"
echo "============================================="

# Create necessary directories
mkdir -p grafana/dashboards
mkdir -p grafana/datasources

# Create Grafana datasource configuration
cat > grafana/datasources/prometheus.yml << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
EOF

# Create Grafana dashboard configuration
cat > grafana/dashboards/dashboard.yml << EOF
apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
EOF

# Create a basic Grafana dashboard JSON
cat > grafana/dashboards/telegram-bot-dashboard.json << 'EOF'
{
  "dashboard": {
    "id": null,
    "title": "Telegram Bot Monitoring",
    "tags": ["telegram", "bot"],
    "style": "dark",
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Active Users",
        "type": "stat",
        "targets": [
          {
            "expr": "telegram_bot_active_users",
            "refId": "A"
          }
        ],
        "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0}
      },
      {
        "id": 2,
        "title": "Concurrent Searches",
        "type": "stat",
        "targets": [
          {
            "expr": "telegram_bot_concurrent_searches",
            "refId": "A"
          }
        ],
        "gridPos": {"h": 8, "w": 6, "x": 6, "y": 0}
      },
      {
        "id": 3,
        "title": "Search Requests Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(telegram_bot_user_search_requests_total[5m]))",
            "refId": "A",
            "legendFormat": "Requests/sec"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
      },
      {
        "id": 4,
        "title": "Average Search Duration",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(telegram_bot_search_duration_seconds_sum[5m]) / rate(telegram_bot_search_duration_seconds_count[5m])",
            "refId": "A",
            "legendFormat": "Avg Duration (s)"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16}
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "5s"
  }
}
EOF

echo "✅ Configuration files created"

# Make scripts executable
chmod +x setup_monitoring.sh

echo ""
echo "🎯 Monitoring Setup Complete!"
echo ""
echo "To start monitoring:"
echo "1. Start the monitoring stack:"
echo "   docker compose -f docker-compose.monitoring.yml up -d"
echo ""
echo "2. Access the services:"
echo "   📊 Task Dashboard: http://localhost:5000"
echo "   📈 Prometheus: http://localhost:9090"
echo "   📊 Grafana: http://localhost:3000 (admin/admin123)"
echo ""
echo "3. Useful Prometheus queries:"
echo "   - Active Users: telegram_bot_active_users"
echo "   - Concurrent Searches: telegram_bot_concurrent_searches"
echo "   - Search Rate: sum(rate(telegram_bot_user_search_requests_total[5m]))"
echo "   - Avg Duration: rate(telegram_bot_search_duration_seconds_sum[5m]) / rate(telegram_bot_search_duration_seconds_count[5m])"
echo ""
echo "4. To stop monitoring:"
echo "   docker compose -f docker-compose.monitoring.yml down"
