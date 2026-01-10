"""
ParserSteel Telegram Bot
Поиск марок стали через Telegram
"""

import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

import config
from handlers import search, analogues, start, help_command, stats, fuzzy_search

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    """Start the bot"""
    # Create application
    application = Application.builder().token(config.BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start.start_command))
    application.add_handler(CommandHandler("help", help_command.help_command))
    application.add_handler(CommandHandler("stats", stats.stats_command))
    application.add_handler(CommandHandler("search", search.search_command))
    application.add_handler(CommandHandler("analogues", analogues.analogues_command))
    application.add_handler(CommandHandler("fuzzy", fuzzy_search.fuzzy_search_command))

    # Register message handlers (for direct text input)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        search.handle_text_message
    ))

    # Register callback handler for inline buttons (Add/Delete)
    application.add_handler(CallbackQueryHandler(search.handle_button_callback))

    # Start bot
    logger.info("Starting ParserSteel Telegram Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
