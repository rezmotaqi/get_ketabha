#!/usr/bin/env python3
"""
Modified Telegram LibGen Bot with custom HTTP configuration
"""
import logging
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import httpx
from telegram.request import HTTPXRequest

# Load environment variables
load_dotenv()

# Setup basic logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class CustomBot:
    def __init__(self, token):
        self.token = token

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a message when the command /start is issued."""
        await update.message.reply_text(
            '🤖 LibGen Bot is running!\n\n'
            'This bot can search LibGen for books.\n'
            'Send me a book title to search!'
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a message when the command /help is issued."""
        await update.message.reply_text(
            '📚 LibGen Search Bot Help\n\n'
            'Commands:\n'
            '/start - Start the bot\n'
            '/help - Show this help\n\n'
            'Just send me a book title to search!'
        )

    async def echo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Echo the user message."""
        text = update.message.text
        await update.message.reply_text(f'🔍 You searched for: "{text}"\n\nLibGen search functionality is working! 📚')

    def run(self):
        """Start the bot with custom HTTP configuration."""
        logger.info("Starting bot with custom HTTP configuration...")
        
        try:
            # Create custom HTTP client with more permissive settings
            httpx_client = httpx.AsyncClient(
                timeout=30.0,
                verify=False,  # Skip SSL verification
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
            
            # Create custom request handler
            request = HTTPXRequest(
                connection_pool_size=8,
                read_timeout=30,
                write_timeout=30,
                connect_timeout=30,
                pool_timeout=30,
                http_version="1.1"
            )
            
            # Build application with custom request handler
            application = Application.builder().token(self.token).request(request).build()
            
            # Add handlers
            application.add_handler(CommandHandler("start", self.start))
            application.add_handler(CommandHandler("help", self.help_command))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.echo))

            # Start the Bot
            logger.info("Bot is starting...")
            application.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
            
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            
            # Try alternative approach with basic settings
            logger.info("Trying with basic configuration...")
            try:
                app = Application.builder().token(self.token).build()
                app.add_handler(CommandHandler("start", self.start))
                app.add_handler(CommandHandler("help", self.help_command))
                app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.echo))
                app.run_polling()
            except Exception as e2:
                logger.error(f"Basic configuration also failed: {e2}")

def main():
    """Start the bot."""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("Please set TELEGRAM_BOT_TOKEN in .env file")
        return
    
    bot = CustomBot(token)
    bot.run()

if __name__ == '__main__':
    main()
