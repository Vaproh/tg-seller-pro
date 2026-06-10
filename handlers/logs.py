from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.permissions import require_admin
from core.format import esc, code, _truncate
from database.logs import get_logs, count_logs, LOGS_PER_PAGE
from datetime import datetime

STATUS_EMOJI = {
    "success": "✅",
    "failed": "❌",
    "denied": "🚫",
    "cancelled": "🚫",
}


def _fmt_log_entry(entry):
    e = dict(entry)
    username = e.get("username") or "—"
    seller_name = e.get("seller_name")
    user_id = e.get("user_id", "?")
    command = e.get("command", "?")
    command_args = e.get("command_args")
    status = e.get("status", "?")
    error_reason = e.get("error_reason")
    error_detail = e.get("error_detail")
    created_at = e.get("created_at", "?")
    status_emoji = STATUS_EMOJI.get(status, "❓")
    seller_line = f"👤 Seller: @{esc(username)}"
    if seller_name:
        seller_line += f" ({esc(seller_name)})"
    text = (
        f"{seller_line}\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"⚡ Command: {code(command)}"
    )
    if command_args:
        text += f"\n📥 Args: {esc(command_args)}"
    text += f"\n{status_emoji} Status: {esc(status)}"
    if status in ("failed", "denied") and error_reason:
        text += f"\n📝 Reason: {esc(error_reason)}"
        if error_detail:
            text += f"\n🔍 Detail: {esc(error_detail)}"
    text += f"\n🕒 Time: <code>{esc(str(created_at)[:19])}</code>"
    return text


def _fmt_logs_page(logs, page, total_pages, filters_desc=""):
    text = f"<b>📜 Activity Log — page {page}/{total_pages}</b>\n"
    if filters_desc:
        text += f"<i>{esc(filters_desc)}</i>\n"
    text += "\n"
    for entry in logs:
        text += _fmt_log_entry(entry) + "\n\n"
    if not logs:
        text += "📭 No logs found."
    return text


def _logs_keyboard(page, total_pages):
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"logs:page:{page - 1}"))
    nav_row.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("➡️", callback_data=f"logs:page:{page + 1}"))
    buttons = [nav_row]
    buttons.append([
        InlineKeyboardButton("❌ Failed", callback_data="logsfilter:failed"),
        InlineKeyboardButton("🚫 Denied", callback_data="logsfilter:denied"),
        InlineKeyboardButton("📋 All", callback_data="logsfilter:all"),
    ])
    buttons.append([
        InlineKeyboardButton("🔐 Permission", callback_data="logsfilter:permission"),
        InlineKeyboardButton("⚠️ Validation", callback_data="logsfilter:validation"),
    ])
    buttons.append([
        InlineKeyboardButton("💾 Database", callback_data="logsfilter:database"),
        InlineKeyboardButton("🔧 System", callback_data="logsfilter:system"),
    ])
    return InlineKeyboardMarkup(buttons)


def _build_filter_desc(filters):
    parts = []
    if filters.get("seller"):
        parts.append(f"Seller: {filters['seller']}")
    if filters.get("command"):
        parts.append(f"Command: {filters['command']}")
    if filters.get("date"):
        parts.append(f"Date: {filters['date']}")
    if filters.get("status"):
        parts.append(f"Status: {filters['status']}")
    if filters.get("category"):
        parts.append(f"Category: {filters['category']}")
    return " | ".join(parts) if parts else ""


async def logs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    args = context.args
    filters = {
        "seller": None, "command": None, "status": None,
        "date": None, "category": None,
    }
    if args:
        i = 0
        while i < len(args):
            arg = args[i].lower()
            if arg == "seller" and i + 1 < len(args):
                filters["seller"] = args[i + 1].lstrip("@")
                i += 2
            elif arg == "command" and i + 1 < len(args):
                filters["command"] = args[i + 1]
                i += 2
            elif arg == "today":
                filters["date"] = datetime.now().strftime("%Y-%m-%d")
                i += 1
            elif arg == "failed":
                filters["status"] = "failed"
                i += 1
            elif arg == "denied":
                filters["status"] = "denied"
                i += 1
            elif arg in ("validation", "permission", "database", "system"):
                filters["category"] = arg
                filters["status"] = "failed"
                i += 1
            else:
                i += 1
    context.user_data["logs_filters"] = filters
    total = count_logs(**filters)
    if total == 0:
        await update.message.reply_text("📭 No logs found.")
        return
    total_pages = max(1, (total + LOGS_PER_PAGE - 1) // LOGS_PER_PAGE)
    logs = get_logs(limit=LOGS_PER_PAGE, offset=0, **filters)
    text = _fmt_logs_page(logs, 1, total_pages, _build_filter_desc(filters))
    kb = _logs_keyboard(1, total_pages)
    await update.message.reply_text(_truncate(text), parse_mode="HTML", reply_markup=kb)


async def logs_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not await require_admin(update):
        return
    await query.answer()
    try:
        page = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        return
    filters = context.user_data.get("logs_filters", {})
    total = count_logs(**filters)
    total_pages = max(1, (total + LOGS_PER_PAGE - 1) // LOGS_PER_PAGE)
    if page < 1 or page > total_pages:
        return
    offset = (page - 1) * LOGS_PER_PAGE
    logs = get_logs(limit=LOGS_PER_PAGE, offset=offset, **filters)
    text = _fmt_logs_page(logs, page, total_pages, _build_filter_desc(filters))
    kb = _logs_keyboard(page, total_pages)
    await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)


async def logs_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not await require_admin(update):
        return
    await query.answer()
    _, filter_value = query.data.split(":", 1)
    filters = context.user_data.get("logs_filters", {})
    if filter_value == "all":
        filters["status"] = None
        filters["category"] = None
    elif filter_value == "failed":
        filters["status"] = "failed"
        filters["category"] = None
    elif filter_value == "denied":
        filters["status"] = "denied"
        filters["category"] = None
    elif filter_value in ("validation", "permission", "database", "system"):
        filters["category"] = filter_value
        filters["status"] = "failed"
    context.user_data["logs_filters"] = filters
    total = count_logs(**filters)
    total_pages = max(1, (total + LOGS_PER_PAGE - 1) // LOGS_PER_PAGE)
    logs = get_logs(limit=LOGS_PER_PAGE, offset=0, **filters)
    text = _fmt_logs_page(logs, 1, total_pages, _build_filter_desc(filters))
    kb = _logs_keyboard(1, total_pages)
    await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
