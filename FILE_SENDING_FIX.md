# File Sending Fix

## Problem
The bot was showing "File too large or send disabled" for files that should be sendable (like 4MB and 30MB files), and falling back to showing download links instead of sending the actual files.

## Root Cause
1. **Missing File Handler Check**: The bot was only checking `self.file_handler` but not `self.truly_parallel_file_handler`
2. **Size Parsing Issue**: The bot wasn't properly parsing file sizes from search results (e.g., "30 MB", "4 MB") to compare with the size limit

## Solution

### 1. Fixed File Handler Check
**Before:**
```python
if self.feature_send_files and self.file_handler:
    await self._send_book_file(query, context, book, title, md5_hash)
```

**After:**
```python
if self.feature_send_files and (self.file_handler or self.truly_parallel_file_handler):
    await self._send_book_file(query, context, book, title, md5_hash)
```

### 2. Added Proper Size Parsing
**Before:**
- No size checking before attempting download
- Files were being rejected without proper size comparison

**After:**
```python
# Parse size string (e.g., "30 MB", "4 MB", "1.2 GB")
size_match = re.search(r'(\d+\.?\d*)\s*([A-Za-z]*)', str(book_size_str))
if size_match:
    value = float(size_match.group(1))
    unit = size_match.group(2).upper() or 'B'
    
    # Convert to MB
    if unit in ['B', 'BYTES']:
        size_mb = value / (1024 * 1024)
    elif unit in ['KB', 'KILOBYTES', 'KBYTES']:
        size_mb = value / 1024
    elif unit in ['MB', 'MEGABYTES', 'MBYTES']:
        size_mb = value
    elif unit in ['GB', 'GIGABYTES', 'GBYTES']:
        size_mb = value * 1024
    
    # Check if file is too large
    if size_mb > self.max_download_mb:
        logger.info(f"File too large: {size_mb:.1f}MB > {self.max_download_mb}MB, showing links instead")
        await self._show_download_links_only(query, context, book, title, md5_hash)
        return
```

## Results

### ✅ **Fixed Issues:**
1. **File Handler Detection**: Bot now properly detects both file handlers
2. **Size Parsing**: Properly parses file sizes from search results
3. **Size Comparison**: Correctly compares parsed sizes with limits
4. **File Sending**: Files under 50MB will now be sent directly instead of showing links

### 📊 **Expected Behavior:**
- **Files ≤ 50MB**: Sent directly through Telegram
- **Files > 50MB**: Show download links (as intended)
- **Unknown Size**: Attempt to download and check during download

### 🚀 **Performance:**
- **Truly Parallel Downloads**: Multiple users can download files simultaneously
- **No Blocking**: Event loop remains responsive during downloads
- **Proper Size Handling**: Accurate size checking before download attempts

## Configuration

The file size limit is controlled by the `TELEGRAM_MAX_DOWNLOAD_MB` environment variable:
- **Default**: 50MB
- **Location**: Environment variables
- **Usage**: Files larger than this limit will show download links instead of being sent directly

## Testing

To test the fix:
1. Search for a book
2. Select a book with size < 50MB
3. The bot should now send the file directly instead of showing download links
4. For files > 50MB, it will still show download links (correct behavior)

## Status: ✅ FIXED

The bot now properly sends files under the size limit directly through Telegram instead of always falling back to download links.
