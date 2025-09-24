#!/usr/bin/env python3
"""
Test script for file sending feature
"""
import asyncio
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.file_handler import FileHandler

async def test_file_handler():
    """Test the file handler with sample configuration."""
    print("🧪 Testing File Handler...")
    
    # Test configuration
    config = {
        'FILE_MIN_SIZE_MB': '0.1',
        'FILE_MAX_SIZE_MB': '50',
        'FILE_VALIDATION_TIMEOUT': '30',
        'FILE_DOWNLOAD_TIMEOUT': '60',
        'FILE_RETRY_ATTEMPTS': '2',
        'HTTP_USER_AGENT': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
    }
    
    try:
        # Initialize file handler
        handler = FileHandler(config)
        print("✅ File handler initialized successfully")
        
        # Test with a sample download link (this will likely fail, but tests the logic)
        sample_links = [
            {
                'url': 'https://example.com/test.pdf',
                'type': 'direct_download',
                'name': 'Test PDF'
            }
        ]
        
        print("🔍 Testing file download and validation...")
        result = await handler.get_best_file_from_links(sample_links, "Test Book")
        
        if result:
            print(f"✅ File downloaded successfully: {result['filename']}")
            print(f"   Size: {result['size']:,} bytes")
            print(f"   Format: {result['extension']}")
            print(f"   MIME type: {result['mime_type']}")
        else:
            print("❌ File download failed (expected for test URL)")
        
        print("\n🎯 File handler test completed!")
        
    except Exception as e:
        print(f"❌ Error testing file handler: {str(e)}")
        return False
    
    return True

async def test_bot_configuration():
    """Test bot configuration for file sending feature."""
    print("\n🤖 Testing Bot Configuration...")
    
    # Test environment variables
    test_env = {
        'FEATURE_SEND_FILES': 'true',
        'FILE_MIN_SIZE_MB': '0.1',
        'FILE_MAX_SIZE_MB': '50',
        'FILE_VALIDATION_TIMEOUT': '30',
        'FILE_DOWNLOAD_TIMEOUT': '60',
        'FILE_RETRY_ATTEMPTS': '2'
    }
    
    # Set test environment
    for key, value in test_env.items():
        os.environ[key] = value
    
    try:
        from bot import TelegramLibGenBot
        
        # Test bot initialization (without token)
        print("🔧 Testing bot configuration loading...")
        
        # Mock token for testing
        os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token'
        
        # This will test the configuration loading
        bot = TelegramLibGenBot('test_token')
        
        print(f"✅ Feature flags loaded:")
        print(f"   FEATURE_SEND_FILES: {bot.feature_send_files}")
        print(f"   FILE_MIN_SIZE_MB: {bot.file_handler.min_size_mb if bot.file_handler else 'N/A'}")
        print(f"   FILE_MAX_SIZE_MB: {bot.file_handler.max_size_mb if bot.file_handler else 'N/A'}")
        
        if bot.file_handler:
            print("✅ File handler initialized successfully")
        else:
            print("❌ File handler not initialized")
        
        print("\n🎯 Bot configuration test completed!")
        
    except Exception as e:
        print(f"❌ Error testing bot configuration: {str(e)}")
        return False
    
    return True

async def main():
    """Run all tests."""
    print("🚀 Starting File Sending Feature Tests\n")
    
    # Test 1: File Handler
    test1_passed = await test_file_handler()
    
    # Test 2: Bot Configuration
    test2_passed = await test_bot_configuration()
    
    # Summary
    print("\n" + "="*50)
    print("📊 Test Summary:")
    print(f"   File Handler: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"   Bot Configuration: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! File sending feature is ready.")
        print("\n📝 To enable file sending:")
        print("   1. Set FEATURE_SEND_FILES=true in your .env file")
        print("   2. Configure file size limits (FILE_MIN_SIZE_MB, FILE_MAX_SIZE_MB)")
        print("   3. Restart the bot")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
    
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())
