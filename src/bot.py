#!/usr/bin/env python3
"""
Telegram LibGen Bot - Main bot file
A Telegram bot that searches LibGen sites for books and returns download links.
"""

import logging
import re
import os
import asyncio
from typing import Optional, List, Dict, Any
from io import BytesIO
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from dotenv import load_dotenv
from telegram.request import HTTPXRequest

from .libgen_search import LibGenSearcher
from .utils.book_formatter import BookFormatter
from .utils.logger import setup_logger
from .utils.file_handler import FileHandler

# Load environment variables
load_dotenv()

# Setup logging
logger = setup_logger(__name__)

class TelegramLibGenBot:
    """Main bot class for LibGen search functionality."""
    
    def __init__(self, token: str):
        """Initialize the bot with Telegram token."""
        self.token = token
        self.searcher = LibGenSearcher()
        self.formatter = BookFormatter()
        
        # Load configuration from environment variables
        self._load_config()
        
        # Initialize file handler if file sending is enabled
        if self.feature_send_files:
            self.file_handler = FileHandler(self._get_file_config())
        else:
            self.file_handler = None
    
    def _load_config(self):
        """Load all configuration from environment variables."""
        # Telegram settings
        send_doc_env = os.getenv('TELEGRAM_SEND_DOCUMENT', 'false').strip().lower()
        self.send_document_enabled = send_doc_env in ['1', 'true', 'yes', 'on']
        try:
            self.max_download_mb = float(os.getenv('TELEGRAM_MAX_DOWNLOAD_MB', '50'))
        except ValueError:
            self.max_download_mb = 50.0
        
        # Bot behavior settings
        self.books_per_page = int(os.getenv('BOT_BOOKS_PER_PAGE', '5'))
        self.max_links_per_book = int(os.getenv('BOT_MAX_LINKS_PER_BOOK', '8'))
        self.download_links_timeout = float(os.getenv('BOT_DOWNLOAD_LINKS_TIMEOUT', '10.0'))
        self.max_alternative_links = int(os.getenv('BOT_MAX_ALTERNATIVE_LINKS', '3'))
        
        # Performance settings
        self.book_processing_delay = float(os.getenv('BOT_BOOK_PROCESSING_DELAY', '0.1'))
        self.cancellation_check_interval = float(os.getenv('BOT_CANCELLATION_CHECK_INTERVAL', '0.25'))
        self.cancellation_checks_count = int(os.getenv('BOT_CANCELLATION_CHECKS_COUNT', '20'))
        
        # Message customization
        self.bot_name = os.getenv('BOT_NAME', 'LibGen Search Bot')
        self.bot_description = os.getenv('BOT_DESCRIPTION', 'Search for books by sending me a book title, author name, or ISBN.')
        
        # Feature flags
        self.feature_download_links = os.getenv('FEATURE_DOWNLOAD_LINKS', 'true').lower() in ['true', '1', 'yes', 'on']
        self.feature_alternative_search = os.getenv('FEATURE_ALTERNATIVE_SEARCH', 'true').lower() in ['true', '1', 'yes', 'on']
        self.feature_pagination = os.getenv('FEATURE_PAGINATION', 'true').lower() in ['true', '1', 'yes', 'on']
        self.feature_stop_command = os.getenv('FEATURE_STOP_COMMAND', 'true').lower() in ['true', '1', 'yes', 'on']
        self.feature_send_files = os.getenv('FEATURE_SEND_FILES', 'false').lower() in ['true', '1', 'yes', 'on']
        
        # HTTP settings
        self.http_user_agent = os.getenv('HTTP_USER_AGENT', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36')
    
    def _get_file_config(self) -> Dict[str, Any]:
        """Get file handling configuration."""
        return {
            'FILE_MIN_SIZE_MB': os.getenv('FILE_MIN_SIZE_MB', '0.1'),
            'FILE_MAX_SIZE_MB': os.getenv('FILE_MAX_SIZE_MB', '50'),
            'FILE_VALIDATION_TIMEOUT': os.getenv('FILE_VALIDATION_TIMEOUT', '30'),
            'FILE_DOWNLOAD_TIMEOUT': os.getenv('FILE_DOWNLOAD_TIMEOUT', '60'),
            'FILE_RETRY_ATTEMPTS': os.getenv('FILE_RETRY_ATTEMPTS', '2'),
            'HTTP_USER_AGENT': self.http_user_agent
        }
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        if not update.message:
            return
            
        welcome_message = (
            f"🤖 **Welcome to {self.bot_name}!**\n\n"
            f"📚 **{self.bot_description}**\n\n"
            "• 📖 Book title\n"
            "• ✍️ Author name  \n"
            "• 🔢 ISBN number\n\n"
            "✨ **Just type your search query to get started!**"
        )
        await update.message.reply_text(welcome_message)
        
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        if not update.message:
            return
            
        help_message = (
            f"📖 **{self.bot_name} Help**\n\n"
            "🤖 **Commands:**\n"
            "• 🏁 `/start` - Start the bot\n"
            "• ❓ `/help` - Show this help\n"
            "• 🔍 `/search <query>` - Search for books\n"
            "• 🛑 `/stop` - Stop current search\n\n"
            "📚 **How to search:**\n"
            "• 📖 Book title: *'The Great Gatsby'*\n"
            "• ✍️ Author name: *'F. Scott Fitzgerald'*\n"
            "• 🔢 ISBN: *'978-0-7432-7356-5'*\n\n"
            "✨ **Features:**\n"
            "🌍 Multiple download sources\n"
            "📥 Direct download links\n"
            "📁 Send files directly (if enabled)\n"
            "📋 Book details (author, year, size, format)\n"
            "⚡ Fast paginated results\n\n"
            "⚠️ **Note:** This bot is for educational purposes only."
        )
        await update.message.reply_text(help_message)
        
    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stop command to cancel current search."""
        if not update.message:
            return
            
        # Set stop flag in user data
        context.user_data['stop_search'] = True
        
        # Clear any cached results
        context.user_data.pop('last_search_results', None)
        context.user_data.pop('download_links', None)
        
        await update.message.reply_text(
            "🛑 **Search stopped!**\n\n"
            "✨ You can start a new search anytime by:\n"
            "• 📖 Sending me a book title\n"
            "• 🔍 Using `/search` command"
        )
        
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /search command with query."""
        if not update.message:
            return
            
        if not context.args:
            await update.message.reply_text("Please provide a search query. Example: /search python programming")
            return
            
        query = ' '.join(context.args)
        await self.handle_search(update, context, query)
        
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages as search queries."""
        if not update.message or not update.message.text:
            return
            
        query = update.message.text.strip()
        if query:
            await self.handle_search(update, context, query)
        else:
            await update.message.reply_text("Please send me a book title, author, or ISBN to search.")
            
    async def handle_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query: str) -> None:
        """Process search query and return results one by one."""
        # Clear any previous stop flag
        context.user_data.pop('stop_search', None)
        
        # Send searching message
        searching_msg = await update.message.reply_text(
            f"🔍 **Searching for:** *'{query}'*..."
        )
        
        try:
            # Perform search
            results = await self.searcher.search(query)
            
            # Check if user stopped search during the search phase
            if context.user_data.get('stop_search'):
                await searching_msg.edit_text("🛑 Search stopped by user request.")
                return
            
            if not results:
                await searching_msg.edit_text(
                    f"❌ **No results found for:** *'{query}'*\n\n"
                    "💡 **Try:**\n"
                    "• Different keywords\n"
                    "• Author name\n"
                    "• Exact book title\n"
                    "• ISBN number"
                )
                return
                
            # Store results for callbacks and update search status
            context.user_data['last_search_results'] = results
            await searching_msg.edit_text(
                f"🎉 **Found {len(results)} results for:** *'{query}'*\n\n"
                f"📤 Sending your results now..."
            )
            
            # Check again before starting to send results
            if context.user_data.get('stop_search'):
                await searching_msg.edit_text("🛑 Search stopped by user request.")
                return
            
            # Send first 5 books immediately without download links
            await self.send_paginated_results(update, context, results, page=0)
                
        except Exception as e:
            logger.error(f"Search error for query '{query}': {str(e)}")
            await searching_msg.edit_text(
                "❌ **Search failed due to an error.**\n\n"
                "Please try again later or contact support if the issue persists."
            )
            
    async def send_paginated_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE, results: List[Dict[str, Any]], page: int = 0) -> None:
        """Send search results in pages with pagination buttons."""
        books_per_page = self.books_per_page
        start_idx = page * books_per_page
        end_idx = min(start_idx + books_per_page, len(results))
        
        if start_idx >= len(results):
            await update.message.reply_text("No more results available.")
            return
        
        page_results = results[start_idx:end_idx]
        
        # Create message with book info (no download links)
        message_parts = []
        for i, book in enumerate(page_results, start_idx + 1):
            try:
                title = book.get('title', 'Unknown Title')
                author = book.get('author', 'Unknown Author')
                year = book.get('year', 'Unknown')
                format_ext = book.get('extension', 'Unknown').upper()
                size = book.get('size', 'Unknown')
                
                book_info = f"📚 <b>{i}. {title}</b>\n\n"
                book_info += f"👤 <b>Author:</b> {author}\n"
                book_info += f"📄 <b>Format:</b> {format_ext}  |  📅 <b>Year:</b> {year}  |  💾 <b>Size:</b> {size}\n\n"
                book_info += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                
                message_parts.append(book_info)
                
            except Exception as e:
                logger.debug(f"Error processing book {i}: {str(e)}")
                simple_info = f"📚 <b>{i}. {book.get('title', 'Unknown')}</b>\n\n"
                simple_info += f"⚠️ <i>Error loading book details</i>\n\n"
                simple_info += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                message_parts.append(simple_info)
        
        # Create message
        message = "".join(message_parts)
        
        # Add page info with emojis
        total_pages = (len(results) + books_per_page - 1) // books_per_page
        message += f"📄 <b>Page {page + 1} of {total_pages}</b>  •  📊 <b>{len(results)} total results</b>"
        
        # Create pagination buttons
        buttons = []
        
        # Row 1: Get Download Links buttons for each book on this page
        link_buttons = []
        for i, _ in enumerate(page_results):
            book_idx = start_idx + i
            link_buttons.append(InlineKeyboardButton(f"📥 Links #{book_idx + 1}", callback_data=f"links_{book_idx}"))
        
        # Split link buttons into rows of 2
        for i in range(0, len(link_buttons), 2):
            buttons.append(link_buttons[i:i+2])
        
        # Row 2: Navigation buttons
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Previous 5", callback_data=f"page_{page-1}"))
        if end_idx < len(results):
            nav_buttons.append(InlineKeyboardButton("➡️ Next 5", callback_data=f"page_{page+1}"))
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        # Send message with buttons
        keyboard = InlineKeyboardMarkup(buttons)
        await update.message.reply_text(
            message,
            parse_mode='HTML',
            disable_web_page_preview=True,
            reply_markup=keyboard
        )

    async def send_batched_results_with_links(self, update: Update, context: ContextTypes.DEFAULT_TYPE, results: List[Dict[str, Any]]) -> None:
        """Send search results in batches of 5 books with download links."""
        batch_size = 5
        
        for batch_start in range(0, len(results), batch_size):
            # Check if user requested to stop
            if context.user_data.get('stop_search'):
                await update.message.reply_text("🛑 Search stopped by user request.")
                return
            
            batch_end = min(batch_start + batch_size, len(results))
            batch_results = results[batch_start:batch_end]
            
            message_parts = []
            
            for i, book in enumerate(batch_results, batch_start + 1):
                # Check for stop request during processing
                if context.user_data.get('stop_search'):
                    await update.message.reply_text("🛑 Search stopped by user request.")
                    return
                    
                try:
                    # Format book details
                    title = book.get('title', 'Unknown Title')
                    author = book.get('author', 'Unknown Author')
                    year = book.get('year', 'Unknown')
                    format_ext = book.get('extension', 'Unknown').upper()
                    size = book.get('size', 'Unknown')
                    md5_hash = book.get('md5', '')
                    
                    book_info = f"<b>{i}. {title}</b>\n"
                    book_info += f"<b>Author:</b> {author}\n"
                    book_info += f"<b>Format:</b> {format_ext} | <b>Year:</b> {year} | <b>Size:</b> {size}\n"
                    
                    # Check for stop request before fetching links
                    if context.user_data.get('stop_search'):
                        await update.message.reply_text("🛑 Search stopped by user request.")
                        return
                    
                    # Get download links for this book
                    if md5_hash:
                        try:
                            # Use a cancellation-aware wrapper for download link fetching
                            download_links = await self._fetch_links_with_cancellation(
                                md5_hash, context, update
                            )
                            
                            # If None returned, it means operation was cancelled
                            if download_links is None:
                                return
                            
                            # Final check for stop request after fetching links
                            if context.user_data.get('stop_search'):
                                await update.message.reply_text("🛑 Search stopped by user request.")
                                return
                            
                            if download_links:
                                book_info += "🔗 **Download Links:**\n"
                                for link in download_links[:8]:  # Show up to 8 links per book
                                    url = link.get('url', '')
                                    if url:
                                        book_info += f"• {url}\n"
                            else:
                                book_info += "❌ **No download links available**\n"
                        except asyncio.TimeoutError:
                            logger.debug(f"Timeout fetching links for {title}")
                            book_info += "⏰ **Timeout fetching links - try manual search**\n"
                        except Exception as e:
                            logger.debug(f"Failed to get links for {title}: {str(e)}")
                            book_info += "❌ **Could not fetch download links**\n"
                    else:
                        # Try alternative search methods for books without MD5
                        alternative_links = await self.get_alternative_search_links(title, author, format_ext)
                        if alternative_links:
                            book_info += "🔍 **Alternative Search Links:**\n"
                            for link in alternative_links[:3]:  # Limit alternative links
                                book_info += f"• {link}\n"
                        else:
                            book_info += "❌ **No MD5 hash available - try manual search**\n"
                    
                    book_info += "\n"
                    message_parts.append(book_info)
                    
                    # Configurable delay between books to allow stop command processing
                    await asyncio.sleep(self.book_processing_delay)
                    
                except Exception as e:
                    logger.debug(f"Error processing book {i}: {str(e)}")
                    simple_info = f"📚 <b>{i}. {book.get('title', 'Unknown')}</b>\n\n"
                    simple_info += f"⚠️ <i>Error loading book details</i>\n\n"
                    simple_info += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    message_parts.append(simple_info)
            
            # Send the batch message
            batch_message = "".join(message_parts)
            if batch_message:
                try:
                    await update.message.reply_text(
                        batch_message,
                        parse_mode='HTML',
                        disable_web_page_preview=True
                    )
                    
                    # Check for stop request after sending each batch
                    if context.user_data.get('stop_search'):
                        await update.message.reply_text("🛑 Search stopped by user request.")
                        return
                        
                except Exception as e:
                    logger.debug(f"Error sending batch message: {str(e)}")
                    # Fallback to plain text
                    await update.message.reply_text(
                        f"📚 **Books {batch_start + 1}-{batch_end}**\n\n"
                        f"⚠️ Error in formatting - please try again"
                    )

    async def get_alternative_search_links(self, title: str, author: str, format_ext: str) -> List[str]:
        """Generate alternative search links for books without MD5 hashes."""
        from urllib.parse import quote
        
        alternative_links = []
        
        # Create search terms
        search_terms = []
        if title and title != 'Unknown Title':
            search_terms.append(quote(title))
        if author and author != 'Unknown Author':
            search_terms.append(quote(author))
        if format_ext and format_ext.upper() != 'UNKNOWN':
            search_terms.append(format_ext.lower())
        
        search_query = '+'.join(search_terms[:3])  # Limit to avoid too long URLs
        
        if search_query:
            # Optimized for English Book Retrieval - Priority Order (September 2025)
            alternative_links.extend([
                # Rank #1: LibGen "Format 2" Mirrors (Top performing for English books)
                f"https://libgen.la/search.php?req={search_query}",
                f"https://libgen.li/search.php?req={search_query}",
                f"https://libgen.gl/search.php?req={search_query}",
                f"https://libgen.vg/search.php?req={search_query}",
                f"https://libgen.bz/search.php?req={search_query}",
                # Rank #2: Anna's Archive (Meta-search aggregating LibGen, Sci-Hub, Z-Library)
                f"https://annas-archive.org/search?q={search_query}",
                f"https://annas-archive.li/search?q={search_query}",
                f"https://annas-archive.se/search?q={search_query}",
                # Rank #3: Z-Library (Large database, good performance)
                f"https://z-library.sk/s/{search_query}",
                # Rank #4: Ocean of PDF (Clean interface, quick downloads)
                f"https://oceanofpdf.com/?s={search_query}",
                # Rank #5: Liber3 (Fast and typically ad-free)
                f"https://liber3.eth.limo/search?q={search_query}",
                # Rank #6: Memory of the World (Solid fallback option)
                f"https://library.memoryoftheworld.org/search?q={search_query}",
                # Additional sources
                f"http://library.lol/search/{search_query}",
                f"https://cyberleninka.ru/search?q={search_query}",
            ])
        
        return alternative_links

    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle button callback queries for pagination and download links."""
        query = update.callback_query
        await query.answer()
        
        if not query.data:
            return
        
        data = query.data
        
        try:
            if data.startswith('page_'):
                # Handle pagination
                page = int(data.split('_')[1])
                results = context.user_data.get('last_search_results', [])
                
                if not results:
                    await query.edit_message_text("❌ Search results expired. Please search again.")
                    return
                
                # Update the message with new page
                await self.send_paginated_results_edit(query, context, results, page)
                
            elif data.startswith('links_'):
                # Handle download links request
                book_idx = int(data.split('_')[1])
                results = context.user_data.get('last_search_results', [])
                
                if not results or book_idx >= len(results):
                    await query.edit_message_text("❌ Book not found. Please search again.")
                    return
                
                book = results[book_idx]
                await self.show_download_links(query, context, book, book_idx)
                
        except Exception as e:
            logger.debug(f"Callback query error: {str(e)}")
            await query.edit_message_text("❌ **Error processing request.**\n\nPlease try again.")

    async def send_paginated_results_edit(self, query, context: ContextTypes.DEFAULT_TYPE, results: List[Dict[str, Any]], page: int) -> None:
        """Edit message with new page of results."""
        books_per_page = self.books_per_page
        start_idx = page * books_per_page
        end_idx = min(start_idx + books_per_page, len(results))
        
        if start_idx >= len(results):
            await query.edit_message_text("No more results available.")
            return
        
        page_results = results[start_idx:end_idx]
        
        # Create message with book info
        message_parts = []
        for i, book in enumerate(page_results, start_idx + 1):
            try:
                title = book.get('title', 'Unknown Title')
                author = book.get('author', 'Unknown Author')
                year = book.get('year', 'Unknown')
                format_ext = book.get('extension', 'Unknown').upper()
                size = book.get('size', 'Unknown')
                
                book_info = f"📚 <b>{i}. {title}</b>\n\n"
                book_info += f"👤 <b>Author:</b> {author}\n"
                book_info += f"📄 <b>Format:</b> {format_ext}  |  📅 <b>Year:</b> {year}  |  💾 <b>Size:</b> {size}\n\n"
                book_info += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                
                message_parts.append(book_info)
                
            except Exception as e:
                logger.debug(f"Error processing book {i}: {str(e)}")
                simple_info = f"📚 <b>{i}. {book.get('title', 'Unknown')}</b>\n\n"
                simple_info += f"⚠️ <i>Error loading book details</i>\n\n"
                simple_info += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                message_parts.append(simple_info)
        
        # Create message
        message = "".join(message_parts)
        
        # Add page info with emojis
        total_pages = (len(results) + books_per_page - 1) // books_per_page
        message += f"📄 <b>Page {page + 1} of {total_pages}</b>  •  📊 <b>{len(results)} total results</b>"
        
        # Create pagination buttons
        buttons = []
        
        # Row 1: Get Download Links buttons for each book on this page
        link_buttons = []
        for i, _ in enumerate(page_results):
            book_idx = start_idx + i
            link_buttons.append(InlineKeyboardButton(f"📥 Links #{book_idx + 1}", callback_data=f"links_{book_idx}"))
        
        # Split link buttons into rows of 2
        for i in range(0, len(link_buttons), 2):
            buttons.append(link_buttons[i:i+2])
        
        # Row 2: Navigation buttons
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Previous 5", callback_data=f"page_{page-1}"))
        if end_idx < len(results):
            nav_buttons.append(InlineKeyboardButton("➡️ Next 5", callback_data=f"page_{page+1}"))
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        # Edit message with new content
        keyboard = InlineKeyboardMarkup(buttons)
        await query.edit_message_text(
            message,
            parse_mode='HTML',
            disable_web_page_preview=True,
            reply_markup=keyboard
        )

    async def show_download_links(self, query, context: ContextTypes.DEFAULT_TYPE, book: Dict[str, Any], book_idx: int) -> None:
        """Show download links or send files for a specific book."""
        title = book.get('title', 'Unknown Title')
        md5_hash = book.get('md5')
        
        if not md5_hash:
            # Show alternative search links for books without MD5
            alternative_links = await self.get_alternative_search_links(
                title, 
                book.get('author', ''), 
                book.get('extension', '')
            )
            
            links_text = f"📚 **{title}**\n\n"
            links_text += f"👤 **Author:** {book.get('author', 'Unknown')}\n"
            links_text += f"📄 **Format:** {book.get('extension', 'Unknown')}  •  📅 **Year:** {book.get('year', 'Unknown')}  •  💾 **Size:** {book.get('size', 'Unknown')}\n\n"
            links_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            if alternative_links:
                links_text += "🔍 **Alternative Search Links:**\n\n"
                for i, link in enumerate(alternative_links[:self.max_alternative_links], 1):
                    links_text += f"🌐 **{i}.** {link}\n\n"
            else:
                links_text += "❌ **No MD5 hash available for direct download links.**"
            
            await query.edit_message_text(
                links_text,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            return
        
        # Check if file sending is enabled
        if self.feature_send_files and self.file_handler:
            await self._send_book_file(query, context, book, title, md5_hash)
        else:
            await self._show_download_links_only(query, context, book, title, md5_hash)
    
    async def _send_book_file(self, query, context: ContextTypes.DEFAULT_TYPE, book: Dict[str, Any], title: str, md5_hash: str) -> None:
        """Send book file directly through Telegram."""
        # Show downloading message
        await query.edit_message_text(f"📁 Downloading file for: {title}...")
        
        try:
            # Get download links
            download_links = await asyncio.wait_for(
                self.searcher.get_download_links(md5_hash), 
                timeout=self.download_links_timeout
            )
            
            if not download_links:
                await query.edit_message_text(
                    f"❌ **No download links found for:** *{title}*\n\n"
                    f"🔍 You can try searching manually with MD5: `{md5_hash}`",
                    parse_mode='Markdown'
                )
                return
            
            # Try to download and validate file
            file_data = await self.file_handler.get_best_file_from_links(download_links, title)
            
            if file_data:
                # Send file as document
                await query.message.reply_document(
                    document=file_data['data'],
                    filename=file_data['filename'],
                    caption=f"📚 **{title}**\n\n"
                           f"👤 **Author:** {book.get('author', 'Unknown')}\n"
                           f"📄 **Format:** {file_data['extension'].upper()}\n"
                           f"💾 **Size:** {file_data['size']:,} bytes\n\n"
                           f"✅ **File sent successfully!**"
                )
                
                # Update the original message
                await query.edit_message_text(
                    f"✅ **File sent successfully!**\n\n"
                    f"📚 **{title}**\n"
                    f"📄 **Format:** {file_data['extension'].upper()}\n"
                    f"💾 **Size:** {file_data['size']:,} bytes"
                )
            else:
                # Fallback to showing links
                await self._show_download_links_only(query, context, book, title, md5_hash)
                
        except asyncio.TimeoutError:
            await query.edit_message_text(
                f"⏰ **Timeout downloading file for:** *{title}*\n\n"
                f"🔄 Falling back to download links..."
            )
            # Fallback to showing links
            await self._show_download_links_only(query, context, book, title, md5_hash)
        except Exception as e:
            logger.debug(f"Error sending file for {title}: {str(e)}")
            await query.edit_message_text(
                f"❌ **Error downloading file for:** *{title}*\n\n"
                f"🔄 Falling back to download links..."
            )
            # Fallback to showing links
            await self._show_download_links_only(query, context, book, title, md5_hash)
    
    async def _show_download_links_only(self, query, context: ContextTypes.DEFAULT_TYPE, book: Dict[str, Any], title: str, md5_hash: str) -> None:
        """Show download links only (fallback method)."""
        # Show getting links message
        await query.edit_message_text(f"🔗 **Getting download links for:** *{title}*...")
        
        try:
            # Get download links with configurable timeout
            download_links = await asyncio.wait_for(
                self.searcher.get_download_links(md5_hash), 
                timeout=self.download_links_timeout
            )
            
            if not download_links:
                await query.edit_message_text(
                    f"❌ **No download links found for:** *{title}*\n\n"
                    f"🔍 You can try searching manually with MD5: `{md5_hash}`",
                    parse_mode='Markdown'
                )
                return
            
            # Format message with download links
            links_text = f"📚 **{title}**\n\n"
            links_text += f"👤 **Author:** {book.get('author', 'Unknown')}\n"
            links_text += f"📄 **Format:** {book.get('extension', 'Unknown')}  •  📅 **Year:** {book.get('year', 'Unknown')}  •  💾 **Size:** {book.get('size', 'Unknown')}\n\n"
            links_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            links_text += "🔗 **Download Links:**\n\n"
            
            for i, link in enumerate(download_links[:self.max_links_per_book], 1):
                url = link.get('url', '')
                if url:
                    links_text += f"📥 **{i}.** {url}\n\n"
            
            links_text += f"🔍 **MD5:** `{md5_hash}`\n\n"
            links_text += "📋 **Copy the links and paste into a browser**"
            
            await query.edit_message_text(
                links_text,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
        except asyncio.TimeoutError:
            await query.edit_message_text(
                f"⏰ **Timeout getting links for:** *{title}*\n\n"
                f"🔍 You can try searching manually with MD5: `{md5_hash}`",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.debug(f"Error getting download links: {str(e)}")
            await query.edit_message_text(
                f"❌ **Error getting links for:** *{title}*\n\n"
                "Please try again later."
            )

    async def _fetch_links_with_cancellation(self, md5_hash: str, context: ContextTypes.DEFAULT_TYPE, update: Update) -> Optional[List[Dict[str, Any]]]:
        """Fetch download links with frequent cancellation checks."""
        async def check_cancellation():
            """Periodically check for stop requests."""
            for _ in range(self.cancellation_checks_count):  # Configurable cancellation checks
                if context.user_data.get('stop_search'):
                    return True
                await asyncio.sleep(self.cancellation_check_interval)
            return False
        
        # Run the download link fetching and cancellation check concurrently
        try:
            done, pending = await asyncio.wait(
                [
                    asyncio.create_task(self.searcher.get_download_links(md5_hash)),
                    asyncio.create_task(check_cancellation())
                ],
                return_when=asyncio.FIRST_COMPLETED,
                timeout=self.download_links_timeout
            )
            
            # Cancel any remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # Check if cancellation was requested
            if context.user_data.get('stop_search'):
                await update.message.reply_text("🛑 Search stopped by user request.")
                return None
            
            # Get the result from the completed download task
            for task in done:
                if not task.cancelled():
                    try:
                        result = task.result()
                        if isinstance(result, list):  # This is the download links result
                            return result
                        elif isinstance(result, bool) and result:  # This is cancellation signal
                            await update.message.reply_text("🛑 Search stopped by user request.")
                            return None
                    except Exception:
                        pass
            
            # If we get here, something went wrong
            return []
            
        except asyncio.TimeoutError:
            logger.debug(f"Timeout fetching links for MD5: {md5_hash}")
            return []
        except Exception as e:
            logger.debug(f"Error in cancellation-aware link fetching: {str(e)}")
            return []

    def _select_best_link(self, links: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Select the best download link to send as a document."""
        if not links:
            return None
        # Prefer direct mirror or resolved direct download with filename
        def link_score(link: Dict[str, Any]) -> int:
            score = 0
            link_type = link.get('type', '')
            if link_type in ['direct_mirror', 'direct_download']:
                score += 2
            if link.get('filename'):
                score += 1
            return score
        return sorted(links, key=link_score, reverse=True)[0]

    async def _send_document_from_url(self, update: Update, url: str, referer: Optional[str] = None, suggested_filename: Optional[str] = None) -> None:
        """Download a file from URL (with size cap) and send as Telegram document with proper filename."""
        headers = {
            'User-Agent': self.http_user_agent
        }
        if referer:
            headers['Referer'] = referer
        timeout = aiohttp.ClientTimeout(total=60)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # HEAD first to get metadata
                filename = suggested_filename
                content_length = None
                content_type = None
                try:
                    async with session.head(url, headers=headers, allow_redirects=True) as head_resp:
                        content_type = head_resp.headers.get('Content-Type')
                        content_length = head_resp.headers.get('Content-Length')
                        disposition = head_resp.headers.get('Content-Disposition', '')
                        if not filename and disposition:
                            filename = self._extract_filename_from_disposition(disposition)
                except Exception:
                    pass
                # Size guard
                try:
                    if content_length:
                        size_mb = int(content_length) / (1024 * 1024)
                        if size_mb > self.max_download_mb:
                            await update.message.reply_text(
                                f"File is too large to send as document (~{size_mb:.1f} MB). Download via link above."
                            )
                            return
                except Exception:
                    pass
                # Download
                async with session.get(url, headers=headers, allow_redirects=True) as get_resp:
                    final_url = str(get_resp.url)
                    if not filename:
                        disposition = get_resp.headers.get('Content-Disposition', '')
                        if disposition:
                            filename = self._extract_filename_from_disposition(disposition)
                    if not filename:
                        filename = self._infer_filename_from_url(final_url) or 'file'
                    # Stream into memory (bounded by max_download_mb)
                    max_bytes = int(self.max_download_mb * 1024 * 1024)
                    buffer = BytesIO()
                    downloaded = 0
                    async for chunk in get_resp.content.iter_chunked(1024 * 64):
                        if not chunk:
                            continue
                        buffer.write(chunk)
                        downloaded += len(chunk)
                        if downloaded > max_bytes:
                            await update.message.reply_text(
                                "Download exceeded size limit; please use the link above."
                            )
                            return
                    buffer.seek(0)
                    await update.message.reply_document(
                        document=buffer,
                        filename=filename,
                        caption=f"📄 {filename}"
                    )
        except Exception as e:
            logger.debug(f"Failed to send document from URL {url}: {e}")
            # Silent failure; links are still provided

    def _extract_filename_from_disposition(self, content_disposition: str) -> Optional[str]:
        if not content_disposition:
            return None
        match_ext = re.search(r"filename\*=(?:UTF-8''|)\s*([^;]+)", content_disposition, flags=re.IGNORECASE)
        if match_ext:
            try:
                from urllib.parse import unquote
                return unquote(match_ext.group(1).strip('"'))
            except Exception:
                return match_ext.group(1).strip('"')
        match = re.search(r'filename="?([^";]+)"?', content_disposition, flags=re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def _infer_filename_from_url(self, url: str) -> Optional[str]:
        try:
            from urllib.parse import urlparse, unquote
            import os as _os
            path = urlparse(url).path
            if not path:
                return None
            name = _os.path.basename(path)
            name = unquote(name)
            return name if name else None
        except Exception:
            return None
            
        
            
    def run(self) -> None:
        """Start the bot."""
        logger.info("Starting Telegram LibGen Bot...")
        
        # Configure proxy if available
        http_proxy = os.getenv('HTTP_PROXY')
        https_proxy = os.getenv('HTTPS_PROXY')
        
        if http_proxy or https_proxy:
            logger.info(f"🔧 Using HTTP proxy: {https_proxy or http_proxy}")
            proxy_url = https_proxy or http_proxy
            # Create HTTPXRequest with proper proxy configuration
            request = HTTPXRequest(proxy_url=proxy_url)
            application = Application.builder().token(self.token).request(request).build()
        else:
            logger.info("🌐 No proxy configured, using direct connection")
            application = Application.builder().token(self.token).build()
        
        # Add handlers based on feature flags
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("search", self.search_command))
        
        if self.feature_stop_command:
            application.add_handler(CommandHandler("stop", self.stop_command))
            
        if self.feature_pagination:
            application.add_handler(CallbackQueryHandler(self.handle_callback_query))
            
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Start the bot
        logger.info("🤖 Bot is running...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Main function to run the bot."""
    # Get bot token from environment
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not bot_token:
        logger.error("❌ TELEGRAM_BOT_TOKEN not found in environment variables!")
        print("❌ Error: Please set TELEGRAM_BOT_TOKEN in your .env file")
        return
        
    # Create and run bot
    bot = TelegramLibGenBot(bot_token)
    
    try:
        bot.run()
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Bot error: {str(e)}")
        

if __name__ == '__main__':
    main()
