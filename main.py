#!/usr/bin/env python3
"""
Main entry point for the Telegram LibGen Bot.
Run this script to start the bot.
"""

import sys
import os

# Add src directory to path to enable imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.bot import main
from src.utils.logger import create_startup_log

if __name__ == "__main__":
    # Create startup log
    create_startup_log()
    
    # Run the bot
    main()
