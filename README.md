# Telegram LibGen Bot 📚🤖

A Telegram bot that searches LibGen sites for books and returns download links. This bot helps users find and access books from various LibGen mirrors with a simple and intuitive interface.

## Features ✨

- 🔍 **Smart Search**: Search by title, author, ISBN, or keywords
- 🌐 **Multiple Mirrors**: Automatically tries different LibGen mirrors for reliability
- 📋 **Rich Results**: Displays book details including author, year, size, format, and pages
- 🔗 **Direct Download Links**: Provides working download links from multiple sources
- ⚡ **Fast & Reliable**: Asynchronous processing for quick responses
- 🎯 **User Friendly**: Simple commands and intuitive interface
- 📝 **Detailed Logging**: Comprehensive logging for debugging and monitoring

## Quick Start 🚀

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/telegram-libgen-bot.git
   cd telegram-libgen-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the bot**
   ```bash
   cp env.template .env
   # Edit .env and add your Telegram Bot Token
   ```

4. **Run the bot**
   ```bash
   python main.py
   ```

## Setup Instructions 📋

### 1. Create a Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` to create a new bot
3. Follow the instructions to set a name and username
4. Copy the bot token (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Install Python Dependencies

Make sure you have Python 3.8 or higher installed, then:

```bash
# Install required packages
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy the template and edit it:

```bash
cp env.template .env
```

Edit `.env` file:
```env
TELEGRAM_BOT_TOKEN=your_actual_bot_token_here
LOG_LEVEL=INFO
MAX_SEARCH_RESULTS=25
SEARCH_TIMEOUT=30
```

### 4. Run the Bot

```bash
# Method 1: Using main.py
python main.py

# Method 2: Running the bot module directly
python -m src.bot

# Method 3: For development with logs visible
python src/bot.py
```

## Project Structure 🏗️

```
telegram-libgen-bot/
├── src/
│   ├── bot.py                 # Main bot logic
│   ├── libgen_search.py       # LibGen search functionality
│   └── utils/
│       ├── __init__.py
│       ├── book_formatter.py  # Message formatting
│       └── logger.py          # Logging utilities
├── logs/                      # Log files (created automatically)
├── main.py                    # Entry point
├── requirements.txt           # Python dependencies
├── env.template              # Environment variables template
├── .env                      # Your actual environment variables (gitignored)
├── .gitignore               # Git ignore rules
└── README.md               # This file
```

## Usage 💬

### Bot Commands

- `/start` - Show welcome message and instructions
- `/help` - Display help information
- `/search <query>` - Search for books (e.g., `/search python programming`)

### Searching

You can search in multiple ways:

1. **Send a message**: Just type your search query
   ```
   Clean Code Robert Martin
   ```

2. **Use the search command**: 
   ```
   /search Design Patterns
   ```

3. **Search by ISBN**: 
   ```
   978-0134685991
   ```

### Example Searches

- `python programming`
- `Clean Code Robert Martin`
- `1984 George Orwell`
- `978-0-7432-7356-5`
- `machine learning`
- `JavaScript: The Good Parts`

## Configuration Options ⚙️

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token | Required |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | INFO |
| `MAX_SEARCH_RESULTS` | Maximum search results to process | 25 |
| `SEARCH_TIMEOUT` | Timeout for search requests (seconds) | 30 |
| `MAX_RETRIES` | Maximum retry attempts for failed requests | 3 |
| `MAX_RESULTS_PER_MESSAGE` | Results shown per message | 5 |
| `REQUESTS_PER_SECOND` | Rate limiting for requests | 2 |

### LibGen Mirrors

The bot automatically tries multiple working LibGen mirrors in order:
- libgen.la (primary)
- libgen.li
- libgen.vg
- libgen.bz
- libgen.gl

These mirrors are based on real-time analysis of working LibGen sites. You can customize the mirror list in your `.env` file using `LIBGEN_SEARCH_MIRRORS` and `LIBGEN_DOWNLOAD_MIRRORS` variables.

## Development 🛠️

### Running in Development Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG  # On Windows: set LOG_LEVEL=DEBUG
python main.py
```

### Testing the Search Module

```bash
# Test the LibGen search functionality
python src/libgen_search.py
```

### Project Dependencies

Key dependencies include:
- `python-telegram-bot`: Telegram Bot API wrapper
- `aiohttp`: Async HTTP client for web requests
- `beautifulsoup4`: HTML parsing for scraping
- `python-dotenv`: Environment variable management

## Troubleshooting 🔧

### Common Issues

1. **"TELEGRAM_BOT_TOKEN not found"**
   - Make sure you've created a `.env` file
   - Check that your bot token is correctly set in `.env`

2. **"No results found"**
   - Try different search terms
   - Check if LibGen mirrors are accessible
   - Some mirrors might be temporarily down

3. **"Search timeout"**
   - Increase `SEARCH_TIMEOUT` in your `.env` file
   - Check your internet connection

4. **Import errors**
   - Make sure all dependencies are installed: `pip install -r requirements.txt`
   - Check Python version (requires 3.8+)

5. **"No download links found"**
   - The bot now follows LibGen's complete flow (ads.php → file page → get.php)
   - Some books might not have working download links
   - Try using the MD5 hash manually on LibGen sites

6. **"404 errors from LibGen"**
   - LibGen mirrors change frequently - the bot uses current working mirrors
   - If persistent, check the `LIBGEN_SEARCH_MIRRORS` in your .env file
   - Update to latest working mirrors: libgen.la, libgen.li, libgen.vg

### Logging

Logs are automatically saved to:
- `logs/bot.log` - General application logs
- `logs/errors.log` - Error logs only

You can also see real-time logs in the console when running the bot.

### Debug Mode

Enable debug logging for detailed information:
```bash
# In your .env file
LOG_LEVEL=DEBUG
```

## Legal Notice ⚖️

This bot is intended for educational and research purposes only. Users are responsible for complying with their local laws regarding copyrighted material. The authors of this bot do not encourage or condone piracy.

## Contributing 🤝

Contributions are welcome! Please feel free to:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/telegram-libgen-bot.git
cd telegram-libgen-bot

# Install development dependencies
pip install -r requirements.txt

# Install pre-commit hooks (optional)
pip install pre-commit
pre-commit install
```

## License 📄

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog 📝

### Version 1.1.0 (LibGen Integration Fixes)
- ✅ **Fixed LibGen search patterns**: Updated to use correct index.php endpoint with proper parameters
- ✅ **Improved HTML parsing**: Now correctly parses the actual LibGen table structure  
- ✅ **Enhanced download links**: Follows the complete LibGen flow (search → results → get.php final download)
- ✅ **Updated working mirrors**: Uses currently active LibGen mirrors (.la, .li, .vg, .bz, .gl)
- ✅ **Better error handling**: Improved fallback mechanisms for failed requests
- ✅ **Real download extraction**: Properly extracts get.php links with keys for direct downloads
- ✅ **Mirror diversity**: Support for RandomBook and Anna's Archive alternative mirrors

### Version 1.0.0 (Initial Release)
- Basic search functionality
- Multiple LibGen mirror support
- Telegram bot interface
- Rich message formatting
- Comprehensive logging
- Download link extraction

## Support 💬

If you encounter any issues or have questions:

1. Check the [Troubleshooting](#troubleshooting-🔧) section
2. Look through existing [GitHub Issues](https://github.com/yourusername/telegram-libgen-bot/issues)
3. Create a new issue with detailed information about your problem

## Acknowledgments 🙏

- LibGen community for maintaining the mirrors
- Python Telegram Bot library developers
- Beautiful Soup and aiohttp library maintainers

---

**Happy Reading! 📚**
