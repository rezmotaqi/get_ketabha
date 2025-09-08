#!/usr/bin/env python3
"""
Telegram LibGen Bot - Main bot file
A Telegram bot that searches LibGen sites for books and returns download links.
"""

import logging
import os
from typing import Optional, List, Dict, Any
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
        """Process search query and return results."""
        # Send searching message
        searching_msg = await update.message.reply_text(f"🔍 Searching for: '{query}'...")
        
        try:
            # Perform search
            results = await self.searcher.search(query)
            
            if not results:
                await searching_msg.edit_text(
                    f"❌ No results found for: '{query}'\n\n"
                    "Try:\n"
                    "• Different keywords\n"
                    "• Author name\n"
                    "• Exact book title\n"
                    "• ISBN number"
                )
                return
                
            # Store results in user context for download callbacks
            context.user_data['last_search_results'] = results[:5]
            
            # Format and send results
            formatted_results = self.formatter.format_search_results(results[:5])  # Limit to 5 results
            keyboard = self.create_download_keyboard(results[:5])
            
            await searching_msg.edit_text(
                f"📚 Found {len(results)} results for: '{query}'\n\n{formatted_results}",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
        except Exception as e:
            logger.error(f"Search error for query '{query}': {str(e)}")
            await searching_msg.edit_text(
                "❌ Search failed due to an error. Please try again later."
            )
            
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
            # Extract book index from callback data
            book_index = int(query.data.split('_')[1])
            
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
                
            # Format download links message
            links_text = f"📚 **{book['title']}**\n"
            links_text += f"👤 Author: {book['author']}\n"
            links_text += f"📅 Year: {book['year']} | 💾 Size: {book['size']} | 📄 Format: {book['extension']}\n\n"
            links_text += "🔗 **Download Links:**\n"
            
            for i, link in enumerate(download_links[:5], 1):  # Limit to 5 links
                link_name = link.get('name') or link.get('text') or 'Download'
                links_text += f"{i}. [{link_name}]({link['url']})\n"
                
            links_text += f"\n🔍 MD5: `{md5_hash}`"
            
            await query.edit_message_text(
                links_text,
                parse_mode='Markdown',
                disable_web_page_preview=True
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
