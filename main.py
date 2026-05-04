"""
═══════════════════════════════════════════════════════════
                    FLASH-UCBOT - MAIN.PY
          Magical Command Loader - No Built-in Commands
═══════════════════════════════════════════════════════════
"""

import asyncio
import time
import os
import importlib
import sys
import logging
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, AuthKeyError, SessionPasswordNeededError
from dotenv import load_dotenv

# ═══════════════════════════════════════════════════════════
#                    LOAD ENVIRONMENT VARIABLES
# ═══════════════════════════════════════════════════════════

load_dotenv()

# ═══════════════════════════════════════════════════════════
#                    CONFIGURATION
# ═══════════════════════════════════════════════════════════

API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
SESSION_STRING = os.getenv('SESSION_STRING')
COMMAND_PREFIX = os.getenv('COMMAND_PREFIX', '.')

# Validate required variables
if not all([API_ID, API_HASH, SESSION_STRING]):
    print("\n" + "═" * 60)
    print("❌ ERROR: Missing Required Environment Variables!")
    print("═" * 60)
    print("\n📋 Required variables:")
    print("   • API_ID")
    print("   • API_HASH")
    print("   • SESSION_STRING")
    print("\n💡 Set these in your .env file or environment variables")
    print("═" * 60 + "\n")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════
#                    LOGGING SETUP
# ═══════════════════════════════════════════════════════════

log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler(
            f'{log_dir}/bot_{datetime.now().strftime("%Y%m%d")}.log',
            encoding='utf-8'
        ),
        logging.StreamHandler()
    ]
)

# Set Telethon logging to WARNING to reduce noise
logging.getLogger('telethon').setLevel(logging.WARNING)

logger = logging.getLogger('FlashBot')

# ═══════════════════════════════════════════════════════════
#                    INITIALIZE CLIENT
# ═══════════════════════════════════════════════════════════

client = TelegramClient(
    StringSession(SESSION_STRING),
    API_ID,
    API_HASH,
    system_version="4.16.30-vxCUSTOM"
)

# Global bot start time
start_time = time.time()
# ═══════════════════════════════════════════════════════════
#              CASE-INSENSITIVE PREFIX HELPER
# ═══════════════════════════════════════════════════════════

def make_prefix_case_insensitive(prefix):
    """
    Converts a prefix to a case-insensitive regex pattern.
    
    Args:
        prefix: Command prefix (e.g., 'A', '.', '!')
    
    Returns:
        str: Case-insensitive regex pattern
    
    Example:
        'A' becomes '[Aa]'
        '.' stays '\\.' (escaped)
        'AB' becomes '[Aa][Bb]'
    """
    import re
    
    pattern = ''.join(
        f'[{c.upper()}{c.lower()}]' if c.isalpha() else re.escape(c)
        for c in prefix
    )
    
    return pattern
# ═══════════════════════════════════════════════════════════
#              MAGICAL COMMAND LOADING SYSTEM
# ═══════════════════════════════════════════════════════════

def load_all_commands():
    """
    ✨ MAGICAL COMMAND LOADER ✨
    
    Automatically discovers and loads ALL command modules from 'commands/' folder.
    Just drop any .py file with a register() function and it loads automatically!
    
    Returns:
        int: Number of successfully loaded commands
    """
    commands_dir = 'commands'
    
    # Create commands directory if it doesn't exist
    if not os.path.exists(commands_dir):
        logger.warning(f"Commands directory not found!")
        os.makedirs(commands_dir)
        
        # Create __init__.py
        init_file = os.path.join(commands_dir, '__init__.py')
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write('"""Commands Package - Auto-generated"""\n')
        
        logger.info(f"Created '{commands_dir}/' directory")
        logger.info(f"💡 Add your command files to '{commands_dir}/' folder")
        return 0
    
    # Get all .py files (excluding __init__ and privates)
    command_files = [
        f[:-3] for f in os.listdir(commands_dir)
        if f.endswith('.py') and not f.startswith('_')
    ]
    
    if not command_files:
        logger.warning(f"No command files found in '{commands_dir}/'")
        logger.info(f"💡 Add .py files to '{commands_dir}/' to load commands")
        return 0
    
    # Sort for consistent loading order
    command_files.sort()
    
    # ✨ NEW: Create case-insensitive prefix pattern
    case_insensitive_prefix = make_prefix_case_insensitive(COMMAND_PREFIX)
    
    loaded_count = 0
    failed_count = 0
    
    print("\n" + "═" * 60)
    print(f"📦 LOADING COMMAND MODULES (Case-Insensitive Mode)")
    print("═" * 60 + "\n")
    
    for command_file in command_files:
        try:
            module_name = f'{commands_dir}.{command_file}'
            
            # Reload if already loaded (for development/hot-reload)
            if module_name in sys.modules:
                module = importlib.reload(sys.modules[module_name])
            else:
                module = importlib.import_module(module_name)
            
            # Check if module has register function
            if hasattr(module, 'register'):
                # ✨ NEW: Pass case-insensitive prefix instead of original
                module.register(client, case_insensitive_prefix)
                loaded_count += 1
                print(f"  ✅ {command_file:30s} → Loaded (Case-Insensitive)")
            else:
                failed_count += 1
                print(f"  ⚠️  {command_file:30s} → No register() function")
                logger.warning(f"Command '{command_file}' missing register() function")
                
        except Exception as e:
            failed_count += 1
            print(f"  ❌ {command_file:30s} → Error")
            logger.error(f"Failed to load '{command_file}': {str(e)}")
    
    print("\n" + "═" * 60)
    print(f"📊 LOADED: {loaded_count} | FAILED: {failed_count} | TOTAL: {loaded_count + failed_count}")
    print("═" * 60 + "\n")
    
    return loaded_count

# ═══════════════════════════════════════════════════════════
#                    MAIN BOT RUNNER
# ═══════════════════════════════════════════════════════════

async def main():
    """
    🚀 Main Bot Startup Function
    
    Handles:
    - Telegram client connection
    - Command module loading
    - Error recovery and auto-restart
    - Graceful shutdown
    """
    
    retry_count = 0
    max_retries = 5
    
    while retry_count < max_retries:
        try:
            # Clear screen and show banner
            os.system('clear' if os.name != 'nt' else 'cls')
            
            print("\n")
            print("╔═══════════════════════════════════════════════════════════╗")
            print("║                                                           ║")
            print("║              ⚡ FLASH-UCBOT INITIALIZING ⚡              ║")
            print("║                                                           ║")
            print("╚═══════════════════════════════════════════════════════════╝")
            print("\n")
            
            # Start Telegram client
            logger.info("🔌 Connecting to Telegram...")
            await client.start()
            
            # Get account information
            me = await client.get_me()
            
            # Display connection success
            print("═" * 60)
            print("✅ TELEGRAM CONNECTION SUCCESSFUL")
            print("═" * 60)
            print(f"👤 Name      : {me.first_name}" + (f" {me.last_name}" if me.last_name else ""))
            print(f"📱 Username  : @{me.username}" if me.username else "📱 Username  : Not Set")
            print(f"🆔 User ID   : {me.id}")
            print(f"📞 Phone     : {me.phone}" if me.phone else "📞 Phone     : Hidden")
            print(f"🔑 Prefix    : '{COMMAND_PREFIX}'")
            print("═" * 60)
            
            # Load all command modules
            loaded_commands = load_all_commands()
            
            if loaded_commands == 0:
                logger.warning("⚠️  No commands loaded! Bot will run but won't respond to commands.")
                logger.info(f"💡 Add command files to '{os.path.abspath('commands')}/'")
            
            # Show ready message
            print("\n" + "╔" + "═" * 58 + "╗")
            print("║" + " " * 58 + "║")
            print("║" + "✨ BOT IS NOW ONLINE AND READY! ✨".center(58) + "║")
            print("║" + " " * 58 + "║")
            print("╚" + "═" * 58 + "╝" + "\n")
            
            logger.info(f"🎯 Monitoring messages with prefix '{COMMAND_PREFIX}'")
            logger.info("⏸️  Press Ctrl+C to stop the bot")
            
            print("\n" + "─" * 60)
            print("📝 BOT ACTIVITY LOG")
            print("─" * 60 + "\n")
            
            # Reset retry count on successful start
            retry_count = 0
            
            # Run until disconnected
            await client.run_until_disconnected()
            
            # Graceful disconnect
            logger.info("Bot disconnected gracefully")
            break
            
        except FloodWaitError as e:
            retry_count += 1
            wait_time = e.seconds
            logger.error(f"⚠️  Flood Wait Error! Must wait {wait_time} seconds")
            logger.info(f"🔄 Retry {retry_count}/{max_retries}")
            
            if retry_count < max_retries:
                logger.info(f"⏳ Waiting {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                logger.info("🔄 Retrying connection...")
            else:
                logger.error(f"❌ Max retries ({max_retries}) reached. Exiting...")
                break
                
        except AuthKeyError:
            logger.error("❌ Authentication Error!")
            logger.error("🔑 Your SESSION_STRING is invalid or expired")
            logger.info("💡 Generate a new session string and update your .env file")
            break
            
        except SessionPasswordNeededError:
            logger.error("❌ 2FA Password Required!")
            logger.error("🔐 Your account has Two-Factor Authentication enabled")
            logger.info("💡 You need to generate SESSION_STRING with 2FA password")
            break
            
        except KeyboardInterrupt:
            logger.info("⏹️  Bot stopped by user (Ctrl+C)")
            break
            
        except Exception as e:
            retry_count += 1
            logger.error(f"❌ Unexpected Error: {str(e)}")
            logger.info(f"🔄 Retry {retry_count}/{max_retries}")
            
            if retry_count < max_retries:
                logger.info("⏳ Waiting 5 seconds before retry...")
                await asyncio.sleep(5)
                logger.info("🔄 Retrying...")
            else:
                logger.error(f"❌ Max retries ({max_retries}) reached. Exiting...")
                break
    
    # Cleanup
    logger.info("🧹 Cleaning up...")
    
    if client.is_connected():
        await client.disconnect()
    
    logger.info("✅ Client disconnected")
    
    print("\n" + "═" * 60)
    print("👋 FLASH-UCBOT SHUTDOWN COMPLETE")
    print("═" * 60 + "\n")

# ═══════════════════════════════════════════════════════════
#                    ENTRY POINT
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    try:
        # Run the bot
        asyncio.run(main())
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user\n")
        
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {str(e)}\n")
        logger.critical(f"Fatal error: {str(e)}", exc_info=True)
        
    finally:
        print("👋 Goodbye!\n")
