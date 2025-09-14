# Telegram LibGen Bot

A powerful Telegram bot that searches Library Genesis (LibGen) for books and provides download links. Built with Python, featuring advanced monitoring, Docker support, and performance optimizations.

## 🚀 Features

### Core Functionality
- **Book Search**: Search LibGen by title, author, or ISBN
- **Download Links**: Get direct download links for found books
- **Alternative Search**: Automatic fallback to alternative LibGen mirrors
- **Pagination**: Navigate through search results with inline keyboards
- **Stop Command**: Cancel ongoing searches
- **Smart Formatting**: Clean, readable book information display

### Advanced Features
- **Real-time Monitoring**: Prometheus metrics integration
- **Performance Tracking**: Request duration and success rate monitoring
- **Concurrent Processing**: Parallel file handling for better performance
- **Error Handling**: Robust error recovery and user feedback
- **Docker Support**: Multiple deployment configurations
- **Logging**: Comprehensive logging with different levels

## 📋 Requirements

- Python 3.8+
- Telegram Bot Token
- Internet connection
- Docker (optional, for containerized deployment)

## 🛠️ Installation

### Method 1: Docker (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd get_ketabha
   ```

2. **Create environment file**
   ```bash
   cp env.template .env
   # Edit .env with your Telegram bot token
   ```

3. **Start with Docker Compose**
   ```bash
   # Production deployment
   docker-compose up -d

   # Development with hot reload
   docker-compose --profile dev up -d

   # Performance-optimized deployment
   docker-compose --profile performance up -d

   # Alpine variant (smaller footprint)
   docker-compose --profile alpine up -d
   ```

### Method 2: Local Installation

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment**
   ```bash
   cp env.template .env
   # Edit .env with your configuration
   ```

3. **Run the bot**
   ```bash
   python main.py
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with the following variables:

```bash
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Optional Configuration
LOG_LEVEL=INFO
LIBGEN_MAX_RESULTS=200
BOT_BOOKS_PER_PAGE=5
LIBGEN_SEARCH_TIMEOUT=30
LIBGEN_MAX_RETRIES=1
BOT_DOWNLOAD_LINKS_TIMEOUT=10
BOT_MAX_LINKS_PER_BOOK=8
BOT_MAX_ALTERNATIVE_LINKS=3
BOT_BOOK_PROCESSING_DELAY=0.1
BOT_CANCELLATION_CHECK_INTERVAL=0.25
BOT_CANCELLATION_CHECKS_COUNT=20

# Feature Flags
FEATURE_DOWNLOAD_LINKS=true
FEATURE_ALTERNATIVE_SEARCH=true
FEATURE_PAGINATION=true
FEATURE_STOP_COMMAND=true
LIBGEN_RESOLVE_FINAL_URLS=true

# Bot Information
BOT_NAME=LibGen Search Bot
BOT_DESCRIPTION=Search for books by sending me a book title, author name, or ISBN.

# HTTP Configuration
HTTP_USER_AGENT=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36

# Proxy Settings (optional)
HTTP_PROXY=
HTTPS_PROXY=
```

## 📱 Usage

### Bot Commands

- **Start**: `/start` - Initialize the bot
- **Help**: `/help` - Show available commands
- **Stop**: `/stop` - Cancel ongoing search operations

### Searching for Books

Simply send a message with:
- Book title
- Author name
- ISBN number
- Any combination of the above

### Example Interactions

```
User: "Python programming"
Bot: [Shows search results with pagination]

User: "Clean Code by Robert Martin"
Bot: [Shows specific book with download links]

User: "9780132350884"
Bot: [Shows book by ISBN]
```

## 📊 Monitoring

The bot includes comprehensive monitoring capabilities:

### Prometheus Metrics
- Search request counts and duration
- Download link resolution metrics
- Error rates and types
- Active user tracking
- System resource usage

### Accessing Metrics
```bash
# View metrics endpoint
curl http://localhost:8000/metrics

# Setup monitoring stack
./monitoring/setup_monitoring.sh
```

### Key Metrics
- `search_requests_total` - Total search requests
- `search_duration_seconds` - Search duration histogram
- `active_users` - Number of active users
- `errors_total` - Error counts by type
- `download_links_resolved` - Download link resolution success rate

## 🏗️ Architecture

```
get_ketabha/
├── src/                    # Source code
│   ├── bot.py             # Main bot implementation
│   ├── libgen_search.py   # LibGen search logic
│   └── utils/             # Utility modules
├── monitoring/            # Monitoring and metrics
├── docker/               # Docker configuration
├── nginx/                # Nginx configuration
├── logs/                 # Log files
├── docker-compose.yml    # Docker Compose configuration
├── Dockerfile           # Multi-stage Docker build
└── main.py              # Application entry point
```

## 🐳 Docker Deployment

### Available Services

1. **libgen-bot** - Production service
2. **libgen-bot-dev** - Development with hot reload
3. **libgen-bot-perf** - Performance-optimized
4. **libgen-bot-alpine** - Minimal Alpine variant
5. **log-aggregator** - Log aggregation (optional)

### Service Profiles

```bash
# Development
docker-compose --profile dev up -d

# Performance
docker-compose --profile performance up -d

# Alpine (minimal)
docker-compose --profile alpine up -d

# With logging
docker-compose --profile logging up -d
```

## 🔧 Development

### Running Tests
```bash
# Run monitoring tests
python monitoring/test_metrics.py

# Run with pytest (if installed)
pytest
```

### Code Structure
- **`src/bot.py`** - Main bot class and handlers
- **`src/libgen_search.py`** - LibGen search implementation
- **`src/utils/`** - Utility modules for file handling, logging, etc.
- **`monitoring/`** - Prometheus metrics and monitoring

### Adding New Features
1. Implement feature in appropriate module
2. Add configuration options to environment variables
3. Update monitoring metrics if needed
4. Test with Docker deployment
5. Update documentation

## 📝 Logging

Logs are stored in the `logs/` directory:
- `bot.log` - General bot operations
- `errors.log` - Error messages
- `monitoring.log` - Monitoring and metrics

## 🚨 Troubleshooting

### Common Issues

1. **Bot not responding**
   - Check Telegram bot token
   - Verify internet connection
   - Check logs for errors

2. **Search not working**
   - Verify LibGen sites are accessible
   - Check timeout settings
   - Review error logs

3. **Docker issues**
   - Ensure Docker and Docker Compose are installed
   - Check container logs: `docker-compose logs libgen-bot`
   - Verify environment variables

### Debug Mode
```bash
# Enable debug logging
LOG_LEVEL=DEBUG docker-compose up

# Or set in .env file
LOG_LEVEL=DEBUG
```

## 📄 License

This project is for educational purposes. Please respect LibGen's terms of service and copyright laws in your jurisdiction.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review logs for error messages
3. Open an issue with detailed information

---

**Note**: This bot is designed to help users find books for educational and research purposes. Please ensure compliance with local laws and respect intellectual property rights.
