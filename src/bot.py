#!/usr/bin/env python3
"""
Telegram LibGen Bot - Main bot file
A Telegram bot that searches LibGen sites for books and returns download links.
"""

import logging
import re
import os
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

from libgen_search import LibGenSearcher
from utils.book_formatter import BookFormatter
from utils.logger import setup_logger

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
        # Optional: send files directly as Telegram documents (ensures proper filename)
        send_doc_env = os.getenv('TELEGRAM_SEND_DOCUMENT', 'false').strip().lower()
        self.send_document_enabled = send_doc_env in ['1', 'true', 'yes', 'on']
        # Max download size in MB when sending as document
        try:
            self.max_download_mb = float(os.getenv('TELEGRAM_MAX_DOWNLOAD_MB', '50'))
        except ValueError:
            self.max_download_mb = 50.0
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        welcome_message = (
            "🤖 Welcome to LibGen Search Bot!\n\n"
            "📚 I can help you find books from LibGen.\n"
            "Simply send me a book title, author name, or ISBN.\n\n"
            "Commands:\n"
            "/start - Show this welcome message\n"
            "/help - Show help information\n"
            "/search <query> - Search for books\n\n"
            "Just type your search query to get started!"
        )
        await update.message.reply_text(welcome_message)
        
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        help_message = (
            "📖 LibGen Search Bot Help\n\n"
            "How to search:\n"
            "• Send book title: 'The Great Gatsby'\n"
            "• Send author name: 'F. Scott Fitzgerald'\n"
            "• Send ISBN: '978-0-7432-7356-5'\n"
            "• Use /search command: '/search python programming'\n\n"
            "Features:\n"
            "✅ Multiple LibGen mirrors\n"
            "✅ Direct download links\n"
            "✅ Book details (author, year, size, format)\n"
            "✅ Fast search results\n\n"
            "Note: This bot is for educational purposes only."
        )
        await update.message.reply_text(help_message)
        
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /search command with query."""
        if not context.args:
            await update.message.reply_text("Please provide a search query. Example: /search python programming")
            return
            
        query = ' '.join(context.args)
        await self.handle_search(update, context, query)
        
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages as search queries."""
        query = update.message.text.strip()
        if query:
            await self.handle_search(update, context, query)
        else:
            await update.message.reply_text("Please send me a book title, author, or ISBN to search.")
            
    async def handle_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query: str) -> None:
        """Process search query and return results one by one."""
        # Send searching message
        searching_msg = await update.message.reply_text(
            f"Searching for: '{query}'...\nCopy the links and paste into a browser"
        )
        
        try:
            # Perform search
            results = await self.searcher.search(query)
            
            if not results:
                await searching_msg.edit_text(
                    f"No results found for: '{query}'\n\n"
                    "Try:\n"
                    "• Different keywords\n"
                    "• Author name\n"
                    "• Exact book title\n"
                    "• ISBN number"
                )
                return
                
            # Store results for callbacks and update search status
            context.user_data['last_search_results'] = results
            await searching_msg.edit_text(
                f"Found {len(results)} results for: '{query}'\nSending results..."
            )
            
            # Send each book result individually with download links
            for i, book in enumerate(results, 1):  # Return ALL results
                await self.send_individual_book_result(update, book, i)
                
        except Exception as e:
            logger.error(f"Search error for query '{query}': {str(e)}")
            await searching_msg.edit_text(
                "Search failed due to an error. Please try again later."
            )
            
    async def send_individual_book_result(self, update: Update, book: Dict[str, Any], index: int) -> None:
        """Send a single book result with its download links."""
        try:
            # Format book details
            title = book.get('title', 'Unknown Title')
            author = book.get('author', 'Unknown Author')
            year = book.get('year', 'Unknown')
            format_ext = book.get('extension', 'Unknown').upper()
            md5_hash = book.get('md5', '')
            
            # Create clean message
            message = f"<b>{index}. {title}</b>\n"
            message += f"<b>Author:</b> {author}\n"
            message += f"<b>Format:</b> {format_ext} | <b>Year:</b> {year}\n\n"
            
            # Provide instruction and a button to get copyable links
            if md5_hash:
                message += (
                    "Tap the button below to get copyable links.\n"
                    f"MD5: <code>{md5_hash}</code>"
                )
            else:
                message += "No download information available."
            
            # Send the individual book result
            keyboard = [[InlineKeyboardButton("🔗 Links (copy)", callback_data=f"download_{index-1}")]]
            await update.message.reply_text(
                message,
                parse_mode='HTML',
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error sending book result {index}: {str(e)}")
            # Send simplified version on error
            simple_message = f"{index}. {book.get('title', 'Unknown')}\nAuthor: {book.get('author', 'Unknown')}\nFormat: {book.get('extension', 'Unknown')}"
            await update.message.reply_text(simple_message)

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
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36'
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
            logger.warning(f"Failed to send document from URL {url}: {e}")
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
            
    def create_download_keyboard(self, results: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
        """Create inline keyboard with download buttons."""
        keyboard = []
        for i, book in enumerate(results):
            button_text = f"📥 Download #{i+1}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"download_{i}")])
        return InlineKeyboardMarkup(keyboard)
        
    async def handle_download_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle download button callbacks."""
        query = update.callback_query
        await query.answer()
        
        try:
            data = query.data or ""

            # Handle copy link callbacks
            if data.startswith('copy_'):
                _, book_idx_str, link_idx_str = data.split('_', 2)
                book_index = int(book_idx_str)
                link_index = int(link_idx_str)

                # Retrieve cached links or fetch if missing
                results = context.user_data.get('last_search_results', [])
                if not results or book_index >= len(results):
                    await query.answer()
                    await query.message.reply_text("❌ Search results expired. Please search again.")
                    return
                links_cache = context.user_data.get('download_links', {})
                links_for_book = links_cache.get(book_index)
                if not links_for_book:
                    md5_hash = results[book_index].get('md5')
                    if not md5_hash:
                        await query.answer()
                        await query.message.reply_text("❌ No MD5 found for this book.")
                        return
                    links_for_book = await self.searcher.get_download_links(md5_hash)
                    links_cache[book_index] = links_for_book or []
                    context.user_data['download_links'] = links_cache

                if not links_for_book or link_index >= len(links_for_book):
                    await query.answer()
                    await query.message.reply_text("❌ Link not available.")
                    return

                url_to_copy = links_for_book[link_index].get('url', '')
                await query.answer("Sent link")
                if url_to_copy:
                    await query.message.reply_text(
                        f"{url_to_copy}\n\nCopy the link and paste into a browser"
                    )
                return

            # Extract book index from download callbacks
            if not data.startswith('download_'):
                await query.answer()
                return
            book_index = int(data.split('_')[1])
            
            # Get the book info from user data (stored during search)
            if 'last_search_results' not in context.user_data:
                await query.edit_message_text("❌ Search results expired. Please search again.")
                return
                
            results = context.user_data['last_search_results']
            if book_index >= len(results):
                await query.edit_message_text("❌ Invalid book selection. Please search again.")
                return
                
            book = results[book_index]
            md5_hash = book.get('md5')
            
            if not md5_hash:
                await query.edit_message_text("❌ No MD5 hash found for this book. Cannot get download links.")
                return
                
            # Show getting links message
            await query.edit_message_text(f"🔗 Getting download links for: {book['title']}...")
            
            # Get download links
            download_links = await self.searcher.get_download_links(md5_hash)
            
            if not download_links:
                await query.edit_message_text(
                    f"❌ No download links found for: {book['title']}\n\n"
                    f"You can try searching manually with MD5: `{md5_hash}`",
                    parse_mode='Markdown'
                )
                return
                
            # Cache links for this book
            links_cache = context.user_data.get('download_links', {})
            links_cache[book_index] = download_links
            context.user_data['download_links'] = links_cache

            # Format message without clickable URLs
            links_text = f"📚 **{book['title']}**\n"
            links_text += f"👤 Author: {book['author']}\n"
            links_text += f"📅 Year: {book['year']} | 💾 Size: {book['size']} | 📄 Format: {book['extension']}\n\n"
            links_text += "🔗 **Download Links (use buttons to copy):**\n"
            for i, link in enumerate(download_links[:5], 1):
                link_name = link.get('name') or link.get('text') or 'Download'
                links_text += f"{i}. {link_name}\n"
            links_text += f"\n🔍 MD5: `{md5_hash}`\n\nCopy the links and paste into a browser"

            # Build copy buttons
            buttons = []
            for i, _ in enumerate(download_links[:5]):
                buttons.append([InlineKeyboardButton(f"Copy link {i+1}", callback_data=f"copy_{book_index}_{i}")])

            await query.edit_message_text(
                links_text,
                parse_mode='Markdown',
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            
        except Exception as e:
            logger.error(f"Download callback error: {str(e)}")
            await query.edit_message_text("❌ Error getting download link. Please try searching again.")
            
    def run(self) -> None:
        """Start the bot."""
        logger.info("Starting Telegram LibGen Bot...")
        
        # Configure proxy if available
        http_proxy = os.getenv('HTTP_PROXY')
        https_proxy = os.getenv('HTTPS_PROXY')
        
        if http_proxy or https_proxy:
            logger.info(f"Using proxy: HTTP={http_proxy}, HTTPS={https_proxy}")
            proxy_url = https_proxy or http_proxy
            request = HTTPXRequest(proxy=proxy_url)
            application = Application.builder().token(self.token).request(request).build()
        else:
            application = Application.builder().token(self.token).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("search", self.search_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        application.add_handler(CallbackQueryHandler(self.handle_download_callback))
        
        # Start the bot
        logger.info("Bot is running...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Main function to run the bot."""
    # Get bot token from environment
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables!")
        print("Error: Please set TELEGRAM_BOT_TOKEN in your .env file")
        return
        
    # Create and run bot
    bot = TelegramLibGenBot(bot_token)
    
    try:
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {str(e)}")
        

if __name__ == '__main__':
    main()
