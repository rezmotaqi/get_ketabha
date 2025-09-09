#!/bin/bash
# =============================================================================
# Docker Entrypoint Script for Telegram LibGen Bot
# =============================================================================

set -e

# Function to log messages
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if required environment variables are set
check_env() {
    if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
        log "ERROR: TELEGRAM_BOT_TOKEN environment variable is not set!"
        log "Please set your bot token in the .env file or environment variables."
        exit 1
    fi
    
    log "Environment check passed"
}

# Function to create necessary directories
setup_directories() {
    log "Setting up directories..."
    mkdir -p /app/logs
    chown -R botuser:botuser /app/logs
    log "Directories created successfully"
}

# Function to wait for network connectivity
wait_for_network() {
    log "Checking network connectivity..."
    max_attempts=30
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if ping -c 1 8.8.8.8 > /dev/null 2>&1; then
            log "Network connectivity confirmed"
            return 0
        fi
        
        log "Network check attempt $attempt/$max_attempts failed, retrying in 2 seconds..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log "WARNING: Network connectivity check failed, but continuing..."
}

# Function to validate bot token
validate_bot_token() {
    log "Validating bot token..."
    
    if python -c "
import os
import requests
import sys

token = os.getenv('TELEGRAM_BOT_TOKEN')
if not token:
    print('ERROR: TELEGRAM_BOT_TOKEN not set')
    sys.exit(1)

try:
    response = requests.get(f'https://api.telegram.org/bot{token}/getMe', timeout=10)
    if response.status_code == 200:
        data = response.json()
        if data.get('ok'):
            print(f'Bot validated: @{data[\"result\"][\"username\"]}')
        else:
            print(f'ERROR: Bot API error: {data.get(\"description\", \"Unknown error\")}')
            sys.exit(1)
    else:
        print(f'ERROR: HTTP {response.status_code}')
        sys.exit(1)
except Exception as e:
    print(f'ERROR: Failed to validate bot token: {e}')
    sys.exit(1)
"; then
        log "Bot token validation successful"
    else
        log "ERROR: Bot token validation failed!"
        exit 1
    fi
}

# Function to run the bot
run_bot() {
    log "Starting Telegram LibGen Bot..."
    log "Bot configuration:"
    log "  - Max results: ${LIBGEN_MAX_RESULTS:-200}"
    log "  - Books per page: ${BOT_BOOKS_PER_PAGE:-5}"
    log "  - Search timeout: ${LIBGEN_SEARCH_TIMEOUT:-30}s"
    log "  - Log level: ${LOG_LEVEL:-INFO}"
    
    # Switch to botuser and run the bot
    exec gosu botuser python main.py
}

# Main execution
main() {
    log "=========================================="
    log "Telegram LibGen Bot - Docker Entrypoint"
    log "=========================================="
    
    # Run setup functions
    check_env
    setup_directories
    wait_for_network
    validate_bot_token
    
    log "All checks passed, starting bot..."
    log "=========================================="
    
    # Start the bot
    run_bot
}

# Handle signals for graceful shutdown
trap 'log "Received shutdown signal, stopping bot..."; exit 0' SIGTERM SIGINT

# Run main function
main "$@"
