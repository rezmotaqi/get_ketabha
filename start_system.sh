#!/bin/bash

# Telegram LibGen Bot System Startup Script
# Starts all components: Bot, Monitoring, and Web Dashboard

set -e

echo "🚀 Starting Telegram LibGen Bot System"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[SYSTEM]${NC} $1"
}

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    print_error "Virtual environment not found. Please run setup first."
    exit 1
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source .venv/bin/activate

# Check if required packages are installed
print_status "Checking dependencies..."
python -c "import telegram, requests, prometheus_client" 2>/dev/null || {
    print_error "Missing required packages. Please install dependencies first."
    exit 1
}

# Kill any existing processes
print_status "Cleaning up existing processes..."
pkill -f "python main.py" 2>/dev/null || true
pkill -f "monitoring import initialize_metrics" 2>/dev/null || true
pkill -f "python -m http.server" 2>/dev/null || true
sleep 2

# Create logs directory
mkdir -p logs

# Start Monitoring System
print_header "Starting Prometheus Monitoring System..."
nohup python -c "
from monitoring import initialize_metrics
import logging
logging.basicConfig(level=logging.INFO)
print('📊 Starting Prometheus monitoring on port 8000...')
initialize_metrics(port=8000)
print('✅ Prometheus monitoring started successfully')
import time
while True:
    time.sleep(1)
" > logs/monitoring.log 2>&1 &
MONITORING_PID=$!

# Wait for monitoring to start
sleep 3

# Verify monitoring is running
if curl -s http://localhost:8000/metrics > /dev/null 2>&1; then
    print_status "✅ Monitoring system started (PID: $MONITORING_PID)"
else
    print_error "❌ Failed to start monitoring system"
    exit 1
fi

# Start Main Bot
print_header "Starting Telegram Bot..."
nohup python main.py > logs/bot.log 2>&1 &
BOT_PID=$!

# Wait for bot to start
sleep 5

# Verify bot is running
if ps -p $BOT_PID > /dev/null 2>&1; then
    print_status "✅ Telegram bot started (PID: $BOT_PID)"
else
    print_error "❌ Failed to start Telegram bot"
    exit 1
fi

# Start Web Server (if not already running)
print_header "Starting Web Dashboard..."
if ! ss -tlnp | grep -q ":8080"; then
    nohup python -m http.server 8080 > logs/web.log 2>&1 &
    WEB_PID=$!
    sleep 2
    print_status "✅ Web server started (PID: $WEB_PID)"
else
    print_warning "⚠️  Web server already running on port 8080"
fi


# Display final status
echo ""
print_header "🎉 System Started Successfully!"
echo "======================================"
echo "📊 Monitoring: http://localhost:8000/metrics"
echo "🤖 Telegram Bot: Running (PID: $BOT_PID)"
echo "🌐 Web Dashboard: http://localhost:8080/"
echo "📈 Prometheus UI: http://localhost:8080/prometheus/"
echo "📊 Grafana UI: http://localhost:8080/grafana/"
echo ""
echo "📁 Logs:"
echo "  - Bot: logs/bot.log"
echo "  - Monitoring: logs/monitoring.log"
echo "  - Web: logs/web.log"
echo ""
echo "🛑 To stop all services: ./stop_system.sh"
echo "📊 To check status: ./check_status.sh"
echo ""

# Keep script running and show live logs
print_header "Showing live bot logs (Ctrl+C to exit):"
echo "=============================================="
tail -f logs/bot.log
