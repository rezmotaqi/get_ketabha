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
        await self.handle_search(update, query)
        
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages as search queries."""
        query = update.message.text.strip()
        if query:
            await self.handle_search(update, query)
        else:
            await update.message.reply_text("Please send me a book title, author, or ISBN to search.")
            
    async def handle_search(self, update: Update, query: str) -> None:
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
            
            # Get download links (this would be implemented based on the last search results)
            # For now, we'll show a placeholder message
            await query.edit_message_text(
                "🔗 Getting download links...\n"
                "This feature will provide direct download links from LibGen mirrors."
            )
            
        except Exception as e:
            logger.error(f"Download callback error: {str(e)}")
            await query.edit_message_text("❌ Error getting download link. Please try searching again.")
            
    def run(self) -> None:
        """Start the bot."""
        logger.info("Starting Telegram LibGen Bot...")
        
        # Create application
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
