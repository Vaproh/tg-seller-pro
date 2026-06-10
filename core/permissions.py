import logging
import config
from database.sellers import get_seller_by_user_id

logger = logging.getLogger(__name__)


def get_user_role(user_id):
    if user_id == config.ADMIN_USER_ID:
        return "admin"
    seller = get_seller_by_user_id(user_id)
    if seller and seller["active"]:
        return "seller"
    return None


def _extract_command_from_update(update):
    if update.message and update.message.text:
        text = update.message.text.strip()
        if text.startswith("/"):
            return text.split()[0].split("@")[0].lower()
    return None


def _log_denied(update, command):
    try:
        from handlers.command_logger import log_denied
        log_denied(update, command)
    except Exception as e:
        logger.error("Failed to log denied attempt: %s", e)


async def require_admin(update):
    user_id = update.effective_user.id
    if get_user_role(user_id) == "admin":
        return True
    logger.warning("Unauthorized admin access from user_id=%s", user_id)
    command = _extract_command_from_update(update)
    if command:
        _log_denied(update, command)
    if update.message:
        await update.message.reply_text("⛔ Admin access required.")
    elif update.callback_query:
        await update.callback_query.answer("⛔ Admin access required.", show_alert=True)
    return False


async def require_seller(update):
    user_id = update.effective_user.id
    if get_user_role(user_id) in ("admin", "seller"):
        return True
    logger.warning("Unauthorized seller access from user_id=%s", user_id)
    command = _extract_command_from_update(update)
    if command:
        _log_denied(update, command)
    if update.message:
        await update.message.reply_text("⛔ You are not authorized to use this bot.")
    elif update.callback_query:
        await update.callback_query.answer("⛔ You are not authorized to use this bot.", show_alert=True)
    return False
