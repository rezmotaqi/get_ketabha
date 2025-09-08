#!/usr/bin/env python3
"""
Book formatter utility for the Telegram LibGen Bot.
Formats book information for display in Telegram messages.
"""

import re
from typing import List, Dict, Any
from utils.logger import setup_logger

logger = setup_logger(__name__)


class BookFormatter:
    """Utility class for formatting book information for Telegram display."""
    
    # File size units for conversion
    SIZE_UNITS = ['B', 'KB', 'MB', 'GB']
    
    # File extension to emoji mapping
    EXTENSION_EMOJIS = {
        'pdf': '📄',
        'epub': '📚',
        'mobi': '📱',
        'azw3': '📱',
        'djvu': '📃',
        'txt': '📝',
        'doc': '📄',
        'docx': '📄',
        'rtf': '📄',
        'fb2': '📖',
        'lit': '📖',
        'pdb': '📱',
        'chm': '📘',
    }
    
    def __init__(self):
        """Initialize the formatter."""
        pass
        
    def format_search_results(self, books: List[Dict[str, Any]]) -> str:
        """
        Format a list of books for display in Telegram.
        
        Args:
            books: List of book dictionaries from search results
            
        Returns:
            Formatted string for Telegram message
        """
        if not books:
            return "No books found."
            
        formatted_results = []
        
        for i, book in enumerate(books, 1):
            formatted_book = self._format_single_book(book, i)
            formatted_results.append(formatted_book)
            
        return '\n\n'.join(formatted_results)
        
    def _format_single_book(self, book: Dict[str, Any], index: int) -> str:
        """Format a single book for display."""
        # Get file extension emoji
        ext = book.get('extension', '').lower()
        emoji = self.EXTENSION_EMOJIS.get(ext, '📄')
        
        # Format title and author
        title = self._truncate_text(book.get('title', 'Unknown Title'), 60)
        author = self._truncate_text(book.get('author', 'Unknown Author'), 40)
        
        # Format year
        year = book.get('year', '')
        year_str = f" ({year})" if year and year.strip() else ""
        
        # Format size
        size = self._format_file_size(book.get('size', ''))
        size_str = f" | {size}" if size != 'Unknown' else ""
        
        # Format pages
        pages = book.get('pages', '')
        pages_str = f" | {pages}p" if pages and pages != 'Unknown' else ""
        
        # Format extension
        extension = ext.upper() if ext else 'Unknown'
        
        # Create formatted string
        result = (
            f"{emoji} <b>{index}. {title}</b>\n"
            f"👤 <i>{author}</i>{year_str}\n"
            f"📋 {extension}{size_str}{pages_str}"
        )
        
        # Add publisher if available
        publisher = book.get('publisher', '').strip()
        if publisher and publisher != 'Unknown':
            publisher = self._truncate_text(publisher, 30)
            result += f"\n🏢 {publisher}"
            
        # Add language if available and not English
        language = book.get('language', '').strip().lower()
        if language and language not in ['english', 'en', '']:
            result += f"\n🌐 {language.title()}"
            
        return result
        
    def format_book_details(self, book: Dict[str, Any]) -> str:
        """
        Format detailed book information for display.
        
        Args:
            book: Book dictionary with detailed information
            
        Returns:
            Formatted string with detailed book information
        """
        # Get file extension emoji
        ext = book.get('extension', '').lower()
        emoji = self.EXTENSION_EMOJIS.get(ext, '📄')
        
        # Basic information
        title = book.get('title', 'Unknown Title')
        author = book.get('author', 'Unknown Author')
        year = book.get('year', '')
        publisher = book.get('publisher', '')
        
        result = f"{emoji} <b>{title}</b>\n\n"
        result += f"👤 <b>Author:</b> {author}\n"
        
        if year and year.strip():
            result += f"📅 <b>Year:</b> {year}\n"
            
        if publisher and publisher.strip():
            result += f"🏢 <b>Publisher:</b> {publisher}\n"
            
        # File information
        size = self._format_file_size(book.get('size', ''))
        pages = book.get('pages', '')
        language = book.get('language', '')
        
        result += f"\n📋 <b>Format:</b> {ext.upper() if ext else 'Unknown'}\n"
        
        if size != 'Unknown':
            result += f"💾 <b>Size:</b> {size}\n"
            
        if pages and pages != 'Unknown':
            result += f"📖 <b>Pages:</b> {pages}\n"
            
        if language and language.strip():
            result += f"🌐 <b>Language:</b> {language.title()}\n"
            
        # MD5 hash (for debugging/verification)
        md5_hash = book.get('md5', '')
        if md5_hash:
            result += f"\n🔑 <b>MD5:</b> <code>{md5_hash}</code>"
            
        return result
        
    def format_download_links(self, links: List[Dict[str, str]]) -> str:
        """
        Format download links for display.
        
        Args:
            links: List of download link dictionaries
            
        Returns:
            Formatted string with download links
        """
        if not links:
            return "❌ No download links available."
            
        formatted_links = ["🔗 <b>Download Links:</b>\n"]
        
        for i, link in enumerate(links, 1):
            url = link.get('url', '')
            text = link.get('text', f'Download {i}')
            mirror = link.get('mirror', '')
            
            # Clean up link text
            clean_text = self._clean_link_text(text)
            
            # Add mirror information if available
            if mirror:
                mirror_name = self._extract_domain_name(mirror)
                clean_text += f" ({mirror_name})"
                
            formatted_links.append(f"🔸 <a href='{url}'>{clean_text}</a>")
            
        return '\n'.join(formatted_links)
        
    def format_search_summary(self, query: str, total_results: int, displayed_results: int) -> str:
        """
        Format search summary information.
        
        Args:
            query: Original search query
            total_results: Total number of results found
            displayed_results: Number of results being displayed
            
        Returns:
            Formatted summary string
        """
        summary = f"🔍 <b>Search:</b> {query}\n"
        summary += f"📊 <b>Results:</b> {total_results} found"
        
        if displayed_results < total_results:
            summary += f" (showing top {displayed_results})"
            
        return summary
        
    def _format_file_size(self, size_str: str) -> str:
        """Convert file size to human-readable format."""
        if not size_str or size_str.strip() in ['0', '', 'Unknown']:
            return 'Unknown'
            
        # Try to extract numeric value and unit
        size_match = re.search(r'(\d+\.?\d*)\s*([A-Za-z]*)', str(size_str))
        
        if not size_match:
            return str(size_str)
            
        try:
            value = float(size_match.group(1))
            unit = size_match.group(2).upper() or 'B'
            
            # Normalize unit
            if unit in ['BYTES']:
                unit = 'B'
            elif unit in ['KILOBYTES', 'KBYTES']:
                unit = 'KB'
            elif unit in ['MEGABYTES', 'MBYTES']:
                unit = 'MB'
            elif unit in ['GIGABYTES', 'GBYTES']:
                unit = 'GB'
                
            # Format based on size
            if unit == 'B' and value >= 1024:
                value /= 1024
                unit = 'KB'
            if unit == 'KB' and value >= 1024:
                value /= 1024
                unit = 'MB'
            if unit == 'MB' and value >= 1024:
                value /= 1024
                unit = 'GB'
                
            # Format number
            if value >= 100:
                return f"{value:.0f} {unit}"
            elif value >= 10:
                return f"{value:.1f} {unit}"
            else:
                return f"{value:.2f} {unit}"
                
        except (ValueError, AttributeError):
            return str(size_str)
            
    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to specified length with ellipsis."""
        if not text:
            return ""
            
        text = str(text).strip()
        
        if len(text) <= max_length:
            return text
            
        return text[:max_length-3] + "..."
        
    def _clean_link_text(self, text: str) -> str:
        """Clean up download link text for display."""
        if not text:
            return "Download"
            
        # Remove common prefixes/suffixes
        clean_text = re.sub(r'^\[.*?\]\s*', '', text)  # Remove [brackets]
        clean_text = re.sub(r'\s*\(.*?\)$', '', clean_text)  # Remove (parentheses)
        clean_text = clean_text.strip()
        
        # Capitalize first letter
        if clean_text:
            clean_text = clean_text[0].upper() + clean_text[1:]
            
        return clean_text or "Download"
        
    def _extract_domain_name(self, url: str) -> str:
        """Extract clean domain name from URL."""
        if not url:
            return ""
            
        try:
            # Remove protocol
            domain = re.sub(r'^https?://', '', url)
            # Remove www.
            domain = re.sub(r'^www\.', '', domain)
            # Take only domain part
            domain = domain.split('/')[0]
            # Remove port
            domain = domain.split(':')[0]
            
            return domain
        except Exception:
            return url
            
    def create_inline_keyboard_text(self, books: List[Dict[str, Any]]) -> str:
        """
        Create text for inline keyboard buttons.
        
        Args:
            books: List of book dictionaries
            
        Returns:
            Text for keyboard buttons
        """
        button_texts = []
        
        for i, book in enumerate(books, 1):
            title = self._truncate_text(book.get('title', 'Unknown'), 30)
            ext = book.get('extension', '').upper()
            emoji = self.EXTENSION_EMOJIS.get(ext.lower(), '📄')
            
            button_text = f"{emoji} {i}. {title}"
            button_texts.append(button_text)
            
        return button_texts


# Example usage and testing
if __name__ == "__main__":
    # Test the formatter
    formatter = BookFormatter()
    
    # Sample book data
    sample_books = [
        {
            'title': 'Clean Code: A Handbook of Agile Software Craftsmanship',
            'author': 'Robert C. Martin',
            'year': '2008',
            'extension': 'pdf',
            'size': '1.2 MB',
            'pages': '464',
            'publisher': 'Prentice Hall',
            'language': 'English',
            'md5': 'abc123def456ghi789jkl012mno345pq'
        },
        {
            'title': 'Python Programming: An Introduction to Computer Science',
            'author': 'John Zelle',
            'year': '2016',
            'extension': 'epub',
            'size': '850 KB',
            'pages': '533',
            'publisher': 'Franklin, Beedle & Associates',
            'language': 'English'
        }
    ]
    
    print("=== Search Results Format ===")
    formatted_results = formatter.format_search_results(sample_books)
    print(formatted_results)
    
    print("\n=== Book Details Format ===")
    detailed_format = formatter.format_book_details(sample_books[0])
    print(detailed_format)
    
    print("\n=== Download Links Format ===")
    sample_links = [
        {'url': 'http://library.lol/main/abc123', 'text': 'GET (library.lol)', 'mirror': 'library.lol'},
        {'url': 'http://libgen.rs/book/index.php?md5=abc123', 'text': 'Libgen.rs', 'mirror': 'libgen.rs'}
    ]
    links_format = formatter.format_download_links(sample_links)
    print(links_format)
