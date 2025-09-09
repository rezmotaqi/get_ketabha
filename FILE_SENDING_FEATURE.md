# 📁 File Sending Feature

This document describes the new file sending feature that allows the Telegram LibGen Bot to send book files directly through Telegram instead of just providing download links.

## 🎯 **Overview**

The file sending feature enables the bot to:
- Download book files from LibGen mirrors
- Validate file integrity, size, and format
- Send files directly through Telegram
- Fall back to download links if file sending fails

## ⚙️ **Configuration**

### Environment Variables

Add these to your `.env` file to enable file sending:

```env
# Enable file sending feature
FEATURE_SEND_FILES=true

# File size limits (in MB)
FILE_MIN_SIZE_MB=0.1
FILE_MAX_SIZE_MB=50

# Download and validation timeouts (in seconds)
FILE_DOWNLOAD_TIMEOUT=60
FILE_VALIDATION_TIMEOUT=30

# Retry attempts for failed downloads
FILE_RETRY_ATTEMPTS=2
```

### Default Values

| Variable | Default | Description |
|----------|---------|-------------|
| `FEATURE_SEND_FILES` | `false` | Enable/disable file sending |
| `FILE_MIN_SIZE_MB` | `0.1` | Minimum file size to send |
| `FILE_MAX_SIZE_MB` | `50` | Maximum file size to send |
| `FILE_DOWNLOAD_TIMEOUT` | `60` | Download timeout in seconds |
| `FILE_VALIDATION_TIMEOUT` | `30` | Validation timeout in seconds |
| `FILE_RETRY_ATTEMPTS` | `2` | Retry attempts for failed downloads |

## 🔧 **How It Works**

### 1. User Interaction
1. User searches for books
2. User clicks "Links" button for a book
3. Bot checks if file sending is enabled

### 2. File Download Process
1. **Get download links** from LibGen mirrors
2. **Try each link** in priority order
3. **Download file** with retry logic
4. **Validate file** (size, format, integrity)
5. **Send file** through Telegram if valid
6. **Fall back to links** if file sending fails

### 3. File Validation
- ✅ **Size validation**: Min 0.1MB, Max 50MB
- ✅ **Format validation**: Supported book formats only
- ✅ **MIME type verification**: Detects actual file type
- ✅ **Integrity check**: Ensures file is not corrupted
- ✅ **Extension validation**: Matches file content to extension

## 📚 **Supported Formats**

| Format | Extension | MIME Type | Description |
|--------|-----------|-----------|-------------|
| **PDF** | `.pdf` | `application/pdf` | Portable Document Format |
| **EPUB** | `.epub` | `application/epub+zip` | Electronic Publication |
| **MOBI** | `.mobi` | `application/x-mobipocket-ebook` | Kindle format |
| **AZW3** | `.azw3` | `application/vnd.amazon.ebook` | Kindle format v3 |
| **DJVU** | `.djvu` | `image/vnd.djvu` | Compressed image format |
| **TXT** | `.txt` | `text/plain` | Plain text |
| **DOC** | `.doc` | `application/msword` | Microsoft Word |
| **DOCX** | `.docx` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | Microsoft Word 2007+ |
| **RTF** | `.rtf` | `application/rtf` | Rich Text Format |
| **FB2** | `.fb2` | `application/x-fictionbook+xml` | FictionBook format |
| **LIT** | `.lit` | `application/x-ms-reader` | Microsoft Reader |
| **PDB** | `.pdb` | `application/vnd.palm` | Palm Database |
| **CHM** | `.chm` | `application/vnd.ms-htmlhelp` | Compiled Help |

## 🏗️ **Technical Implementation**

### File Handler Class (`src/utils/file_handler.py`)

```python
class FileHandler:
    """Handles file downloading, validation, and preparation for Telegram."""
    
    async def download_and_validate_file(self, url: str, expected_filename: str = None) -> Optional[Dict[str, Any]]
    async def get_best_file_from_links(self, download_links: List[Dict[str, str]], book_title: str = None) -> Optional[Dict[str, Any]]
```

### Bot Integration (`src/bot.py`)

```python
# Check if file sending is enabled
if self.feature_send_files and self.file_handler:
    await self._send_book_file(query, context, book, title, md5_hash)
else:
    await self._show_download_links_only(query, context, book, title, md5_hash)
```

### Dependencies

- `python-magic==0.4.27` - File type detection
- `aiohttp` - Async HTTP downloads
- `libmagic1` - System library for file type detection

## 🚀 **Usage Examples**

### Enable File Sending

```bash
# 1. Edit .env file
echo "FEATURE_SEND_FILES=true" >> .env
echo "FILE_MAX_SIZE_MB=50" >> .env

# 2. Restart bot
python main.py
```

### Docker Usage

```bash
# 1. Set environment variables
export FEATURE_SEND_FILES=true
export FILE_MAX_SIZE_MB=50

# 2. Run with Docker
docker-compose up -d
```

### Test File Sending

```bash
# Run test script
python test_file_sending.py
```

## 🔍 **Error Handling**

### Download Failures
- **Timeout**: Falls back to download links
- **Network error**: Retries with exponential backoff
- **Invalid response**: Tries next download link

### Validation Failures
- **File too small**: Rejects files < 0.1MB
- **File too large**: Rejects files > 50MB
- **Unsupported format**: Rejects unsupported file types
- **Corrupted file**: Rejects files that fail integrity checks

### Fallback Behavior
- If file sending fails, bot automatically shows download links
- User gets the same experience regardless of success/failure
- No data loss or broken functionality

## 📊 **Performance Considerations**

### Memory Usage
- Files are streamed in chunks (8KB) to minimize memory usage
- Maximum file size is limited to 50MB by default
- Files are processed in memory without temporary disk storage

### Network Usage
- Retry logic with exponential backoff
- Configurable timeouts to prevent hanging
- Priority-based link selection (direct downloads first)

### CPU Usage
- File validation is lightweight
- MIME type detection is fast
- Minimal processing overhead

## 🛡️ **Security Features**

### File Validation
- **MIME type verification**: Ensures file matches expected type
- **Size limits**: Prevents oversized file attacks
- **Format validation**: Only allows supported book formats
- **Integrity checks**: Detects corrupted files

### Error Handling
- **Graceful degradation**: Falls back to links on failure
- **No data exposure**: Failed downloads don't expose sensitive data
- **Timeout protection**: Prevents hanging on slow downloads

## 🔧 **Troubleshooting**

### Common Issues

#### File Download Fails
```bash
# Check network connectivity
curl -I https://libgen.la

# Check bot logs
docker-compose logs -f libgen-bot
```

#### File Validation Fails
```bash
# Check file size limits
echo "FILE_MIN_SIZE_MB=0.01" >> .env
echo "FILE_MAX_SIZE_MB=100" >> .env

# Restart bot
docker-compose restart
```

#### MIME Type Detection Fails
```bash
# Install libmagic (Ubuntu/Debian)
sudo apt-get install libmagic1 libmagic-dev

# Install libmagic (Alpine)
apk add file-dev
```

### Debug Mode

```bash
# Enable debug logging
echo "LOG_LEVEL=DEBUG" >> .env

# Run test script
python test_file_sending.py
```

## 📈 **Future Enhancements**

### Planned Features
- **File caching**: Cache downloaded files for faster access
- **Compression**: Compress files before sending
- **Progress indicators**: Show download progress to users
- **Batch sending**: Send multiple files at once
- **Format conversion**: Convert between supported formats

### Configuration Options
- **Custom file filters**: User-defined file validation rules
- **Per-user limits**: Different file size limits per user
- **Format preferences**: User-specific format preferences
- **Download scheduling**: Schedule downloads for off-peak hours

## 🎯 **Best Practices**

### For Users
- Keep file size limits reasonable (10-50MB)
- Monitor bot performance with file sending enabled
- Test with different file formats
- Use debug mode for troubleshooting

### For Developers
- Always implement fallback to download links
- Validate files thoroughly before sending
- Handle errors gracefully
- Monitor memory usage with large files
- Test with various file formats and sizes

---

**The file sending feature provides a seamless way to deliver books directly through Telegram while maintaining security, performance, and reliability! 📚✨**
