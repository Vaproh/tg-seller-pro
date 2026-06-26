import logging
from telegram import Bot
from core.format import code_id, code, esc
import config

logger = logging.getLogger(__name__)


async def notify_admin(context, message):
    try:
        await context.bot.send_message(chat_id=config.ADMIN_USER_ID, text=message, parse_mode="HTML")
    except Exception as e:
        logger.error("Failed to notify admin: %s", e)


def fmt_void_notification(sale_code):
    return f"♻️ {code(sale_code)} voided — account returned to stock"


def fmt_seller_added(name, user_id):
    return f"👤 New seller: {esc(name)} (ID: {code_id(user_id)})"


def fmt_seller_removed(name, user_id):
    return f"🚫 Seller removed: {esc(name)} (ID: {code_id(user_id)})"


def fmt_bulk_import(added, skipped, category):
    return f"📥 Bulk import: {added} added, {skipped} skipped in {code(category or '—')}"



