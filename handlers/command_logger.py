import logging
import traceback
from telegram import Update
from telegram.ext import ContextTypes
from database.logs import record_command, ERROR_CATEGORIES
from database.sellers import get_seller_by_user_id

logger = logging.getLogger("commands")

_SENSITIVE_KEYS = {"password", "email_password", "token", "secret", "session"}


def _get_error_category(error_reason):
    if not error_reason:
        return "unknown"
    reason_lower = error_reason.lower()
    for category in ERROR_CATEGORIES:
        if category in reason_lower:
            return category
    return "unknown"


def _extract_user_info(update):
    user = update.effective_user
    username = user.username or user.first_name or "unknown"
    user_id = user.id
    seller = get_seller_by_user_id(user_id)
    seller_name = seller["name"] if seller else None
    return user_id, username, seller_name


def _sanitize_args(raw_args):
    if not raw_args:
        return None
    sanitized = []
    for part in raw_args:
        lower = part.lower()
        if any(k in lower for k in _SENSITIVE_KEYS):
            sanitized.append("***")
        else:
            sanitized.append(part)
    return " ".join(sanitized) if sanitized else None


def _extract_command_args(update):
    if not update.message or not update.message.text:
        return None
    text = update.message.text.strip()
    parts = text.split()
    if len(parts) <= 1:
        return None
    raw_args = parts[1:]
    return _sanitize_args(raw_args)


def _log_to_db(user_id, username, seller_name, command, status,
               command_args=None, error_reason=None, error_detail=None):
    try:
        record_command(
            user_id, username, seller_name, command, status,
            command_args=command_args, error_reason=error_reason,
            error_detail=error_detail,
        )
    except Exception as e:
        logger.error("Failed to log command to DB: %s", e)


async def log_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    if not text.startswith("/"):
        return
    command = text.split()[0].split("@")[0].lower()
    user_id, username, seller_name = _extract_user_info(update)
    command_args = _extract_command_args(update)
    _log_to_db(user_id, username, seller_name, command, "success", command_args=command_args)
    logger.info(
        "CMD %s by %s (%s) [chat=%s]",
        text, update.effective_user.full_name or username,
        user_id, update.effective_chat.id if update.effective_chat else "?",
    )


def log_failure(update, command, error_reason, error_detail=None):
    user_id, username, seller_name = _extract_user_info(update)
    command_args = _extract_command_args(update)
    category = _get_error_category(error_reason)
    detail = f"[{category}] {error_detail}" if error_detail else f"[{category}]"
    _log_to_db(user_id, username, seller_name, command, "failed",
               command_args=command_args, error_reason=error_reason,
               error_detail=detail)


def log_denied(update, command):
    user_id, username, seller_name = _extract_user_info(update)
    command_args = _extract_command_args(update)
    _log_to_db(user_id, username, seller_name, command, "denied",
               command_args=command_args, error_reason="Permission denied",
               error_detail="[permission] User lacks required role")


def log_exception(update, command, exc):
    user_id, username, seller_name = _extract_user_info(update)
    command_args = _extract_command_args(update)
    tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
    tb_text = "".join(tb)[-500:]
    _log_to_db(user_id, username, seller_name, command, "failed",
               command_args=command_args, error_reason=str(exc)[:200],
               error_detail=f"[system] {tb_text}")
