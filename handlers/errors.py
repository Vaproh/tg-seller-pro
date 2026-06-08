import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception while handling an update:", exc_info=context.error)
    if update and hasattr(update, "message") and update.message:
        try:
            await update.message.reply_text("⚠️ An error occurred. Please try again.")
        except Exception:
            pass
    elif update and hasattr(update, "callback_query") and update.callback_query:
        try:
            await update.callback_query.answer("⚠️ An error occurred. Please try again.", show_alert=True)
        except Exception:
            pass
