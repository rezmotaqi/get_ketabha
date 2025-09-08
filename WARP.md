# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Quick Start Commands

### Running the Bot
```bash
# Main entry point
python main.py

# Alternative ways to run
python -m src.bot
python src/bot.py  # Direct execution with console logs
```

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment (copy and edit)
cp .env.template .env

# Test search functionality independently
python src/libgen_search.py

# Enable debug logging
set LOG_LEVEL=DEBUG  # Windows
# export LOG_LEVEL=DEBUG  # Linux/macOS
python main.py
```

### Testing Individual Components
```bash
# Test search module with example queries
python src/libgen_search.py

# Test book formatter with sample data
python src/utils/book_formatter.py

# Test logger configuration
python src/utils/logger.py
```

## Architecture Overview

This is an **async Telegram bot** that searches LibGen (Library Genesis) mirrors for books and returns formatted results with download links.

### Core Architecture Patterns

**Three-Layer Architecture:**
1. **Bot Layer** (`src/bot.py`): Telegram interface and user interaction
2. **Search Layer** (`src/libgen_search.py`): LibGen mirror scraping and data extraction  
3. **Utility Layer** (`src/utils/`): Formatting, logging, and shared functionality

**Key Design Decisions:**
- **Mirror Fallback Strategy**: Automatically tries multiple LibGen mirrors (`libgen.rs`, `libgen.is`, `libgen.st`, `libgen.fun`) until one succeeds
- **Async HTTP Processing**: Uses `aiohttp` for concurrent requests to LibGen mirrors with timeout and retry handling
- **Deduplication Logic**: Removes duplicate books using MD5 hash as primary key, fallback to title+author combination
- **Rate Limiting**: Built-in request throttling to avoid overwhelming LibGen servers

### Data Flow
```
User Query → Bot Handler → LibGenSearcher → HTML Parser → BookFormatter → Telegram Response
                                ↓
                        (tries multiple mirrors)
                                ↓  
                        BeautifulSoup scraping → Book metadata extraction
```

### Critical Components

**TelegramLibGenBot Class:**
- Handles all Telegram commands (`/start`, `/help`, `/search`) and text messages
- Manages search state and creates inline keyboards for download links
- Integrates with `LibGenSearcher` and `BookFormatter`

**LibGenSearcher Class:**
- **Mirror Management**: Maintains list of working LibGen URLs with automatic failover
- **HTML Parsing**: Extracts book metadata from LibGen search result tables
- **Download Link Resolution**: Fetches direct download URLs using MD5 hashes
- **Error Handling**: Comprehensive timeout, retry, and mirror fallback logic

**BookFormatter Class:**
- Formats search results for Telegram's HTML markup
- Handles file size conversion and text truncation
- Maps file extensions to emojis for visual appeal
- Creates inline keyboard button text

### Environment Configuration

Required: `TELEGRAM_BOT_TOKEN` from BotFather
Optional tuning: `MAX_SEARCH_RESULTS`, `SEARCH_TIMEOUT`, `MAX_RETRIES`, `LOG_LEVEL`

### Key File Relationships

- `main.py`: Entry point that imports and runs `src.bot.main()`
- `src/bot.py`: Core bot logic, depends on `libgen_search.LibGenSearcher` and `utils.book_formatter.BookFormatter`
- `src/libgen_search.py`: Independent search module that can be run standalone for testing
- `src/utils/`: Shared utilities used across the application
  - `logger.py`: Configures rotating file logs and console output
  - `book_formatter.py`: Telegram message formatting with HTML markup

### External Dependencies Critical to Functionality
- `python-telegram-bot`: Telegram Bot API wrapper (v20.7)
- `aiohttp`: Async HTTP client for LibGen requests  
- `beautifulsoup4`: HTML parsing for scraping LibGen results
- `python-dotenv`: Environment variable management

### Common Development Workflows

**Adding New LibGen Mirrors:**
Edit `LIBGEN_MIRRORS` list in `LibGenSearcher` class

**Modifying Search Results Display:**
Update `BookFormatter._format_single_book()` method

**Adding New Bot Commands:**
1. Add handler method to `TelegramLibGenBot` class
2. Register handler in `run()` method using `application.add_handler()`

**Debug Search Issues:**
1. Run `python src/libgen_search.py` to test search without Telegram
2. Enable `LOG_LEVEL=DEBUG` to see detailed HTTP requests and parsing
3. Check `logs/bot.log` for detailed error information

### Logging Structure
- **logs/bot.log**: General application logs (rotating, 10MB max)
- **logs/errors.log**: Error-level logs only (rotating, 5MB max)
- Console output shows INFO level and above
- File logs capture DEBUG level with detailed context
