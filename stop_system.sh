#!/bin/bash

# Telegram LibGen Bot System Stop Script
# Stops all running components

set -e

echo "🛑 Stopping Telegram LibGen Bot System"
echo "====================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Stop Bot
print_status "Stopping Telegram Bot..."
if pkill -f "python main.py" 2>/dev/null; then
    print_status "✅ Telegram bot stopped"
else
    print_warning "⚠️  No bot process found"
fi

# Stop Monitoring
print_status "Stopping Monitoring System..."
if pkill -f "monitoring import initialize_metrics" 2>/dev/null; then
    print_status "✅ Monitoring system stopped"
else
    print_warning "⚠️  No monitoring process found"
fi

# Stop Web Server
print_status "Stopping Web Server..."
if pkill -f "python -m http.server 8080" 2>/dev/null; then
    print_status "✅ Web server stopped"
else
    print_warning "⚠️  No web server process found"
fi

# Wait for processes to stop
sleep 2

# Check if any processes are still running
REMAINING=$(ps aux | grep -E "(python main.py|monitoring import|http.server)" | grep -v grep | wc -l)

if [ "$REMAINING" -gt 0 ]; then
    print_warning "⚠️  Some processes may still be running:"
    ps aux | grep -E "(python main.py|monitoring import|http.server)" | grep -v grep
    echo ""
    print_status "Force stopping remaining processes..."
    pkill -9 -f "python main.py" 2>/dev/null || true
    pkill -9 -f "monitoring import" 2>/dev/null || true
    pkill -9 -f "http.server" 2>/dev/null || true
fi


print_status "🎉 All services stopped successfully!"
