#!/usr/bin/env python3
"""
Telegram LibGen Bot - Main bot file
A Telegram bot that searches LibGen sites for books and returns download links.
"""

import logging
import re
import os
import asyncio
import time
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
from .utils.logger import setup_logger
from .utils.http_client import get_http_client, close_http_client, record_request_performance
from .utils.book_formatter import BookFormatter
# Monitoring disabled by user request

# Load environment variables
load_dotenv('/app/.env')

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
        
        # Initialize optimized HTTP client
        self.http_client = get_http_client()
        
        # Initialize file handlers if file sending is enabled
        # File handling disabled - only download links
        self.file_handler = None
        self.concurrent_file_handler = None
        self.truly_parallel_file_handler = None
        
        # Initialize metrics integration - DISABLED
        logger.info("📊 Prometheus monitoring disabled by user request")
        self.metrics = None
        self.metrics_integration = None
            
        # Performance tracking
        self.search_stats = {
            'total_searches': 0,
            'successful_searches': 0,
            'failed_searches': 0,
            'average_response_time': 0.0,
            'total_downloads': 0,
            'total_uploads': 0,
            'average_download_speed': 0.0,
            'average_upload_speed': 0.0,
            'total_download_size_mb': 0.0,
            'total_upload_size_mb': 0.0
        }
    
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
        self.download_links_timeout = float(os.getenv('BOT_DOWNLOAD_LINKS_TIMEOUT', '15.0'))
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
    
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        if not update.message:
            return
            
        welcome_message = f"🤖 **{self.bot_name}**\n\nType your search query to start!"
        await update.message.reply_text(welcome_message)
        
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        if not update.message:
            return
            
        help_message = (
            f"📖 **{self.bot_name} Help**\n\n"
            "**Commands:**\n"
            "• `/start` - Start the bot\n"
            "• `/help` - Show this help\n"
            "• `/search <query>` - Search for books\n"
            "• `/stats` - Show bot stats\n"
            "• `/stop` - Stop current search\n\n"
            "**How to search:**\n"
            "• Book title: *'The Great Gatsby'*\n"
            "• Author name: *'F. Scott Fitzgerald'*\n"
            "• ISBN: *'978-0-7432-7356-5'*"
        )
        await update.message.reply_text(help_message)
        
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stats command to show bot performance statistics."""
        if not update.message:
            return
            
        stats = self.search_stats
        success_rate = (stats['successful_searches'] / stats['total_searches'] * 100) if stats['total_searches'] > 0 else 0
        
        # Get mirror status
        mirror_status = self.searcher._get_mirror_status()
        
        stats_message = (
            f"📊 **{self.bot_name} Stats**\n\n"
            f"**Search:** {stats['total_searches']} total, {success_rate:.1f}% success\n"
            f"**Response Time:** {stats['average_response_time']:.2f}s avg\n"
            f"**Downloads:** {stats['total_downloads']} files\n"
            f"**Uploads:** {stats['total_uploads']} files\n\n"
            f"**Mirrors:** {mirror_status['available_mirrors']}/{mirror_status['total_mirrors']} available\n"
            f"**Failed:** {mirror_status['failed_mirrors']} mirrors"
        )
        await update.message.reply_text(stats_message)
        
    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stop command to cancel current search."""
        if not update.message:
            return
            
        # Set stop flag in user data
        context.user_data['stop_search'] = True
        
        # Clear any cached results
        context.user_data.pop('last_search_results', None)
        context.user_data.pop('download_links', None)
        
        await update.message.reply_text("🛑 Search stopped!")
        
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /search command with query."""
        if not update.message:
            return
            
        if not context.args:
            await update.message.reply_text("❌ Please provide a search query")
            return
            
        query = ' '.join(context.args)
        # Create task and don't await - let search run in background for true concurrency
        asyncio.create_task(self._handle_search_non_blocking(update, context, query))
        
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages as search queries."""
        if not update.message or not update.message.text:
            return
            
        query = update.message.text.strip()
        if query:
            # Create a completely non-blocking task
            asyncio.create_task(self._handle_search_non_blocking(update, context, query))
        else:
            # Send immediate response for empty messages
            await update.message.reply_text("Send a book title, author, or ISBN to search.")
    
    async def _handle_search_non_blocking(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query: str) -> None:
        """Completely non-blocking search handler."""
        try:
            # Send instant response first
            searching_msg = await update.message.reply_text("🔍 Searching... Please wait!")
            
            # Now call the search handler with the message
            await self.handle_search_with_message(update, context, query, searching_msg)
        except Exception as e:
            logger.error(f"Error in non-blocking search: {e}")
            try:
                await update.message.reply_text("❌ An error occurred during search. Please try again.")
            except:
                pass
            
    async def handle_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query: str) -> None:
        """Process search query and return results immediately."""
        import time
        
        # Get user information for logging
        user_id = update.effective_user.id if update.effective_user else "Unknown"
        username = update.effective_user.username if update.effective_user and update.effective_user.username else "NoUsername"
        user_name = update.effective_user.first_name if update.effective_user and update.effective_user.first_name else "NoName"
        
        # Log search request with user details
        logger.info(f"🔍 SEARCH REQUEST - User ID: {user_id} | Username: @{username} | Query: '{query}'")
        print(f"🔍 {query} / {user_name} / @{username}")
        
        # Clear any previous stop flag
        context.user_data.pop('stop_search', None)
        
        # Track search performance
        start_time = time.time()
        self.search_stats['total_searches'] += 1
        
        # Send immediate response message
        searching_msg = await update.message.reply_text("🔍 Searching... Please wait!")
        print(f"📤 Searching... / {user_name} / @{username}")
        
        # Process search immediately (synchronous for this user)
        await self._process_search_immediate(update, context, query, searching_msg, start_time, user_id)

    async def _process_search_immediate(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query: str, searching_msg, start_time: float, user_id: str) -> None:
        """Process search immediately and return results."""
        try:
            # Get user info for real-time logging
            username = update.effective_user.username if update.effective_user and update.effective_user.username else "NoUsername"
            user_name = update.effective_user.first_name if update.effective_user and update.effective_user.first_name else "NoName"
            
            # Perform search
            print(f"🔍 Processing search... / {user_name} / @{username}")
            results = await self.searcher.search(query)
            
            # Calculate response time
            response_time = time.time() - start_time
            self.search_stats['successful_searches'] += 1
            
            # Log completion
            logger.info(f"✅ SEARCH COMPLETED - {response_time:.2f}s | User: {user_id} | Query: '{query}' | Results: {len(results) if results else 0}")
            print(f"✅ Found {len(results) if results else 0} results ({response_time:.1f}s) / {user_name} / @{username}")
            
            if not results:
                await searching_msg.edit_text(f"❌ No results found for *'{query}'*")
                print(f"❌ No results found / {user_name} / @{username}")
                return
                
            # Store results for callbacks
            context.user_data['last_search_results'] = results
            await searching_msg.edit_text(f"✅ Found {len(results)} results for: *'{query}'*")
            print(f"📚 Sending {len(results)} results / {user_name} / @{username}")
            
            # Send first page of results immediately
            await self.send_paginated_results(update, context, results, page=0)
                
        except Exception as e:
            self.search_stats['failed_searches'] += 1
            response_time = time.time() - start_time
            logger.error(f"❌ SEARCH ERROR - User: {user_id} | Query: '{query}' | Time: {response_time:.2f}s | Error: {str(e)}")
            await searching_msg.edit_text(f"❌ Search failed for: '{query}'")

    async def handle_search_with_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query: str, searching_msg) -> None:
        """Process search query with pre-sent message for instant response."""
        import time
        
        # Get user information for logging
        user_id = update.effective_user.id if update.effective_user else "Unknown"
        username = update.effective_user.username if update.effective_user and update.effective_user.username else "NoUsername"
        
        # Log search request with user details
        logger.info(f"🔍 TRUE CONCURRENT SEARCH - User ID: {user_id} | Username: @{username} | Query: '{query}'")
        
        # Metrics disabled by user request
        
        # Clear any previous stop flag
        context.user_data.pop('stop_search', None)
        
        # Track search performance
        start_time = time.time()
        self.search_stats['total_searches'] += 1
        
        # Log that we're starting the search task
        logger.info(f"🚀 Starting TRUE CONCURRENT search task for user {user_id} - query: '{query}'")
        
        # Process search in background
        await self._process_search_background(update, context, query, searching_msg, start_time, user_id)
    
    async def _process_search_background(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query: str, searching_msg, start_time: float, user_id: str) -> None:
        """Process search in background to allow true concurrency."""
        # Get username for metrics
        username = update.effective_user.username if update.effective_user and update.effective_user.username else "NoUsername"
        
        try:
            # searching_msg should already be sent, but check just in case
            if searching_msg is None:
                searching_msg = await update.message.reply_text("🔍 Searching... Please wait!")
            
            # Perform search with performance tracking and timeout protection
            search_task = asyncio.create_task(self.searcher.search(query))
            
            # Add timeout protection to prevent hanging
            try:
                results = await asyncio.wait_for(search_task, timeout=60.0)  # 60 second timeout
            except asyncio.TimeoutError:
                logger.warning(f"Search timeout for query: '{query}'")
                await searching_msg.edit_text(f"⏰ Search timed out for: '{query}'")
                return
            
            # Check if user stopped search during the search phase
            if context.user_data.get('stop_search'):
                await searching_msg.edit_text("🛑 Search stopped")
                return
            
            # Calculate response time
            response_time = time.time() - start_time
            self.search_stats['successful_searches'] += 1
            
            # Update average response time
            total_successful = self.search_stats['successful_searches']
            current_avg = self.search_stats['average_response_time']
            self.search_stats['average_response_time'] = (
                (current_avg * (total_successful - 1) + response_time) / total_successful
            )
            
            # Log performance with concurrency info
            logger.info(f"✅ TRUE CONCURRENT SEARCH COMPLETED - {response_time:.2f}s | User: {user_id} | Query: '{query}' | Results: {len(results) if results else 0}")
            record_request_performance(f"true_concurrent_search:{query}", response_time)
            
            # Record metrics
            # Metrics disabled by user request
            
            if not results:
                await searching_msg.edit_text(f"❌ No results found for *'{query}'*")
                return
                
            # Store results for callbacks and update search status
            context.user_data['last_search_results'] = results
            logger.info(f"📤 Sending results to user {user_id}: {len(results)} results for '{query}'")
            await searching_msg.edit_text(f"✅ Found {len(results)} results for: *'{query}'*")
            
            # Check again before starting to send results
            if context.user_data.get('stop_search'):
                await searching_msg.edit_text("🛑 Search stopped")
                return
            
            # Send first 5 books immediately without download links
            logger.info(f"📚 Sending paginated results to user {user_id}")
            await self.send_paginated_results(update, context, results, page=0)
                
        except Exception as e:
            self.search_stats['failed_searches'] += 1
            response_time = time.time() - start_time
            logger.error(f"❌ TRUE CONCURRENT SEARCH ERROR - User: {user_id} | Query: '{query}' | Time: {response_time:.2f}s | Error: {str(e)}")
            record_request_performance(f"true_concurrent_search_error:{query}", response_time)
            
            # Record error metrics
            # Metrics disabled by user request
            
            await searching_msg.edit_text(f"❌ Search failed for: '{query}'")
            
    async def send_paginated_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE, results: List[Dict[str, Any]], page: int = 0) -> None:
        """Send search results in pages with pagination buttons."""
        books_per_page = self.books_per_page
        start_idx = page * books_per_page
        end_idx = min(start_idx + books_per_page, len(results))
        
        if start_idx >= len(results):
            await update.message.reply_text("❌ No more results")
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
                
                book_info = f"📚 <b>{i}. {title}</b>\n"
                book_info += f"👤 {author}  •  📄 {format_ext}  •  📅 {year}  •  💾 {size}\n\n"
                
                message_parts.append(book_info)
                
            except Exception as e:
                logger.debug(f"Error processing book {i}: {str(e)}")
                simple_info = f"📚 <b>{i}. {book.get('title', 'Unknown')}</b>\n"
                simple_info += f"⚠️ Error loading details\n\n"
                message_parts.append(simple_info)
        
        # Create message
        message = "".join(message_parts)
        
        # Add page info with emojis
        total_pages = (len(results) + books_per_page - 1) // books_per_page
        message += f"📄 Page {page + 1}/{total_pages}  •  📊 {len(results)} results"
        
        # Create pagination buttons
        buttons = []
        
        # Row 1: Get Download Links buttons for each book on this page
        link_buttons = []
        for i, _ in enumerate(page_results):
            book_idx = start_idx + i
            link_buttons.append(InlineKeyboardButton(f"📥 {book_idx + 1} 📥", callback_data=f"links_{book_idx}"))
        
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
                await update.message.reply_text("🛑 Search stopped")
                return
            
            batch_end = min(batch_start + batch_size, len(results))
            batch_results = results[batch_start:batch_end]
            
            message_parts = []
            
            for i, book in enumerate(batch_results, batch_start + 1):
                # Check for stop request during processing
                if context.user_data.get('stop_search'):
                    await update.message.reply_text("🛑 Search stopped")
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
                        await update.message.reply_text("🛑 Search stopped")
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
                                await update.message.reply_text("🛑 Search stopped")
                                return
                            
                            if download_links:
                                book_info += "🔗 **Links:**\n"
                                for link in download_links[:8]:  # Show up to 8 links per book
                                    url = link.get('url', '')
                                    if url:
                                        book_info += f"• {url}\n"
                            else:
                                book_info += "❌ No links available\n"
                        except asyncio.TimeoutError:
                            logger.debug(f"Timeout fetching links for {title}")
                            book_info += "⏰ Timeout - try manual search\n"
                        except Exception as e:
                            logger.debug(f"Failed to get links for {title}: {str(e)}")
                            book_info += "❌ Could not fetch links\n"
                    else:
                        # Try alternative search methods for books without MD5
                        alternative_links = await self.get_alternative_search_links(title, author, format_ext)
                        if alternative_links:
                            book_info += "🔍 **Search Links:**\n"
                            for link in alternative_links[:3]:  # Limit alternative links
                                book_info += f"• {link}\n"
                        else:
                            book_info += "❌ No MD5 hash - try manual search\n"
                    
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
                        await update.message.reply_text("🛑 Search stopped")
                        return
                        
                except Exception as e:
                    logger.debug(f"Error sending batch message: {str(e)}")
                    # Fallback to plain text
                    await update.message.reply_text(f"❌ Error formatting books {batch_start + 1}-{batch_end}")

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
                    await query.edit_message_text("❌ Results expired. Search again.")
                    return
                
                # Update the message with new page
                await self.send_paginated_results_edit(query, context, results, page)
                
            elif data.startswith('links_'):
                # Handle download links request
                book_idx = int(data.split('_')[1])
                results = context.user_data.get('last_search_results', [])
                
                if not results or book_idx >= len(results):
                    await query.edit_message_text("❌ Book not found. Search again.")
                    return
                
                book = results[book_idx]
                await self.show_download_links(query, context, book, book_idx)
                
        except Exception as e:
            logger.debug(f"Callback query error: {str(e)}")
            await query.edit_message_text("❌ Error processing request. Try again.")

    async def send_paginated_results_edit(self, query, context: ContextTypes.DEFAULT_TYPE, results: List[Dict[str, Any]], page: int) -> None:
        """Edit message with new page of results."""
        books_per_page = self.books_per_page
        start_idx = page * books_per_page
        end_idx = min(start_idx + books_per_page, len(results))
        
        if start_idx >= len(results):
            await query.edit_message_text("❌ No more results")
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
                
                book_info = f"📚 <b>{i}. {title}</b>\n"
                book_info += f"👤 {author}  •  📄 {format_ext}  •  📅 {year}  •  💾 {size}\n\n"
                
                message_parts.append(book_info)
                
            except Exception as e:
                logger.debug(f"Error processing book {i}: {str(e)}")
                simple_info = f"📚 <b>{i}. {book.get('title', 'Unknown')}</b>\n"
                simple_info += f"⚠️ Error loading details\n\n"
                message_parts.append(simple_info)
        
        # Create message
        message = "".join(message_parts)
        
        # Add page info with emojis
        total_pages = (len(results) + books_per_page - 1) // books_per_page
        message += f"📄 Page {page + 1}/{total_pages}  •  📊 {len(results)} results"
        
        # Create pagination buttons
        buttons = []
        
        # Row 1: Get Download Links buttons for each book on this page
        link_buttons = []
        for i, _ in enumerate(page_results):
            book_idx = start_idx + i
            link_buttons.append(InlineKeyboardButton(f"📥 {book_idx + 1} 📥", callback_data=f"links_{book_idx}"))
        
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
        
        # Get user information for logging
        user_id = query.from_user.id if query.from_user else "Unknown"
        username = query.from_user.username if query.from_user and query.from_user.username else "NoUsername"
        book_size = book.get('size', 'Unknown')
        book_author = book.get('author', 'Unknown')
        book_format = book.get('extension', 'Unknown')
        
        # Log book request with detailed information
        logger.info(f"📚 BOOK REQUEST - User ID: {user_id} | Username: @{username} | Book: '{title}' | Author: {book_author} | Size: {book_size} | Format: {book_format}")
        
        if not md5_hash:
            # Show alternative search links for books without MD5
            alternative_links = await self.get_alternative_search_links(
                title, 
                book.get('author', ''), 
                book.get('extension', '')
            )
            
            links_text = f"📚 **{title}**\n"
            links_text += f"👤 {book.get('author', 'Unknown')}  •  📄 {book.get('extension', 'Unknown')}  •  📅 {book.get('year', 'Unknown')}  •  💾 {book.get('size', 'Unknown')}\n\n"
            
            if alternative_links:
                links_text += "🔍 **Search Links:**\n\n"
                for i, link in enumerate(alternative_links[:self.max_alternative_links], 1):
                    links_text += f"🌐 **{i}.** {link}\n\n"
            else:
                links_text += "❌ No MD5 hash available"
            
            await query.edit_message_text(
                links_text,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            return
        
        # Always show download links (file sending disabled)
        await self._show_download_links_only(query, context, book, title, md5_hash)
    
    async def _show_download_links_only(self, query, context: ContextTypes.DEFAULT_TYPE, book: Dict[str, Any], title: str, md5_hash: str) -> None:
        """Show download links only."""
        # Get user information for logging
        user_id = query.from_user.id if query.from_user else "Unknown"
        username = query.from_user.username if query.from_user and query.from_user.username else "NoUsername"
        user_name = query.from_user.first_name if query.from_user and query.from_user.first_name else "NoName"
        book_size = book.get('size', 'Unknown')
        
        # Log download links request
        logger.info(f"🔗 DOWNLOAD LINKS - User ID: {user_id} | Username: @{username} | Book: '{title}' | Size: {book_size} | Reason: File too large or send disabled")
        print(f"🔗 {title} / {user_name} / @{username}")
        
        # Show getting links message
        await query.edit_message_text(f"🔗 Getting links for *{title}*...")
        print(f"📤 Getting links... / {user_name} / @{username}")
        
        try:
            # Get download links with configurable timeout
            print(f"🔍 Processing download links... / {user_name} / @{username}")
            download_links = await asyncio.wait_for(
                self.searcher.get_download_links(md5_hash), 
                timeout=self.download_links_timeout
            )
            
            if not download_links:
                await query.edit_message_text(
                    f"❌ No download links found for *{title}*\n\n"
                    f"🔍 Try manual search with MD5: `{md5_hash}`",
                    parse_mode='Markdown'
                )
                return
            
            # Send book info first
            book_info = f"📚 **{title}**\n"
            book_info += f"👤 {book.get('author', 'Unknown')}  •  📄 {book.get('extension', 'Unknown')}  •  📅 {book.get('year', 'Unknown')}  •  💾 {book.get('size', 'Unknown')}\n\n"
            book_info += f"🔗 **Download Links ({len(download_links)} available):**\n"
            book_info += f"🔍 **MD5:** `{md5_hash}`"
            
            await query.edit_message_text(
                book_info,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
            # Send each download link as a separate message
            for i, link in enumerate(download_links[:self.max_links_per_book], 1):
                url = link.get('url', '')
                link_type = link.get('type', 'direct_download')
                link_name = link.get('name', 'Download')
                
                if url:
                    # Extract domain from URL for display
                    try:
                        from urllib.parse import urlparse
                        domain = urlparse(url).netloc
                        if domain:
                            source_info = f" ({domain})"
                        else:
                            source_info = ""
                    except:
                        source_info = ""
                    
                    # Send individual link message
                    link_message = f"📥 **{i}.** {link_name}{source_info}\n\n{url}"
                    
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=link_message,
                        parse_mode='Markdown',
                        disable_web_page_preview=True
                    )
                    
                    # Small delay between messages to avoid rate limiting
                    await asyncio.sleep(0.5)
            
            # Log successful completion of download links display
            logger.info(f"✅ LINKS DISPLAYED - User ID: {user_id} | Username: @{username} | Book: '{title}' | Links Count: {len(download_links[:self.max_links_per_book])} | Size: {book_size}")
            print(f"✅ Found {len(download_links)} download links / {user_name} / @{username}")
            print(f"📤 Sent {len(download_links)} download links / {user_name} / @{username}")
            
        except asyncio.TimeoutError:
            await query.edit_message_text(
                f"⏰ Timeout getting links for *{title}*\n\n"
                f"🔍 Try manual search with MD5: `{md5_hash}`",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.debug(f"Error getting download links: {str(e)}")
            await query.edit_message_text(
                f"❌ Error getting links for *{title}*\n\n"
                "Try again later."
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
                await update.message.reply_text("🛑 Search stopped")
                return None
            
            # Get the result from the completed download task
            for task in done:
                if not task.cancelled():
                    try:
                        result = task.result()
                        if isinstance(result, list):  # This is the download links result
                            return result
                        elif isinstance(result, bool) and result:  # This is cancellation signal
                            await update.message.reply_text("🛑 Search stopped")
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
                            await update.message.reply_text(f"File too large (~{size_mb:.1f} MB). Use link above.")
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
                    
                    # Set up percentage tracking for console
                    content_length = get_resp.headers.get('Content-Length')
                    total_size = int(content_length) if content_length else None
                    last_reported_percent = -1
                    
                    async for chunk in get_resp.content.iter_chunked(1024 * 64):
                        if not chunk:
                            continue
                        buffer.write(chunk)
                        downloaded += len(chunk)
                        
                        # Show percentage progress
                        if total_size:
                            current_percent = int((downloaded / total_size) * 100)
                            if current_percent != last_reported_percent and current_percent % 20 == 0:
                                size_mb = downloaded / (1024 * 1024)
                                total_mb = total_size / (1024 * 1024)
                                print(f"🤖 Bot download progress: {current_percent}% ({size_mb:.1f}MB / {total_mb:.1f}MB) - {filename}")
                                last_reported_percent = current_percent
                        else:
                            # If no total size, show downloaded amount every 10MB
                            if downloaded % (10 * 1024 * 1024) == 0:
                                size_mb = downloaded / (1024 * 1024)
                                print(f"🤖 Bot downloaded: {size_mb:.1f}MB - {filename}")
                        
                        if downloaded > max_bytes:
                            await update.message.reply_text("Download too large. Use link above.")
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
        """Start the bot with optimized concurrency settings."""
        logger.info("Starting Telegram LibGen Bot with concurrent processing...")
        
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
            # Use optimized HTTPXRequest for better concurrency
            request = HTTPXRequest(
                connection_pool_size=100,  # Increased connection pool
                read_timeout=30,
                write_timeout=30,
                connect_timeout=30
            )
            application = Application.builder().token(self.token).request(request).build()
        
        # Add handlers based on feature flags
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("search", self.search_command))
        application.add_handler(CommandHandler("stats", self.stats_command))
        
        if self.feature_stop_command:
            application.add_handler(CommandHandler("stop", self.stop_command))
            
        if self.feature_pagination:
            application.add_handler(CallbackQueryHandler(self.handle_callback_query))
            
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Configure concurrency settings
        logger.info("Configuring bot for concurrent processing...")
        logger.info(f"Max connections: 100, Keep-alive: 20, Timeout: 30s")
        
        # Start the bot with optimized polling settings
        logger.info("Bot is running with concurrent processing enabled...")
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True  # Clear any pending updates
        )


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
        logger.info("Starting optimized Telegram LibGen Bot...")
        bot.run()
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
    finally:
        # Cleanup HTTP client resources
        try:
            close_http_client()
            logger.info("HTTP client resources cleaned up")
        except Exception as e:
            logger.warning(f"Error during cleanup: {str(e)}")
        

if __name__ == '__main__':
    main()
