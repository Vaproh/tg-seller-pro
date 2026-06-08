import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger("commands")


async def log_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    user = update.effective_user
    text = update.message.text
    logger.info(
        "CMD %s by %s (%s) [chat=%s]",
        text,
        user.full_name or user.username or "unknown",
        user.id,
        update.effective_chat.id if update.effective_chat else "?",
    )
