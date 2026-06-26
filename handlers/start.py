import time
from telegram import Update
from telegram.ext import ContextTypes
from core.permissions import require_seller, get_user_role
from core.keyboards import main_menu_keyboard
from core.help_content import HELP_MAIN_ADMIN, HELP_MAIN_SELLER
from database import count_accounts
from database.sales import count_sales, get_sales_summary
import config


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    role = get_user_role(update.effective_user.id)
    is_admin = role == "admin"
    keyboard = main_menu_keyboard(is_admin=is_admin)
    text = HELP_MAIN_ADMIN if is_admin else HELP_MAIN_SELLER
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return

    now = time.time()

    start_time = context.bot_data.get("start_time")
    if start_time:
        uptime_secs = int(now - start_time)
        days, remainder = divmod(uptime_secs, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_parts = []
        if days:
            uptime_parts.append(f"{days}d")
        if hours:
            uptime_parts.append(f"{hours}h")
        if minutes:
            uptime_parts.append(f"{minutes}m")
        uptime_parts.append(f"{seconds}s")
        uptime_str = " ".join(uptime_parts)
    else:
        uptime_str = "unknown"

    msg_time = update.message.date.timestamp()
    latency_ms = int((now - msg_time) * 1000)
    if latency_ms < 1000:
        latency_str = f"{latency_ms}ms"
    else:
        latency_str = f"{latency_ms / 1000:.2f}s"

    available = count_accounts(status="available")
    sold = count_accounts(status="sold")
    pending = count_accounts(status="pending_payment")
    total = available + sold + pending
    summary = get_sales_summary()
    total_sales = count_sales()

    text = (
        f"🏓 <b>Bot Status</b>\n\n"
        f"⏱ Uptime: {uptime_str}\n"
        f"📡 Latency: {latency_str}\n"
        f"💰 Revenue: {config.CURRENCY}{summary.get('total_revenue', 0):.0f}\n"
        f"💳 Pending: {config.CURRENCY}{summary.get('pending_amount', 0):.0f}\n\n"
        f"📦 Accounts: {total} total\n"
        f"🟢 Available: {available}\n"
        f"🔴 Sold: {sold}\n"
        f"🟡 Pending: {pending}\n\n"
        f"🧾 Total sales: {total_sales}"
    )
    await update.message.reply_text(text, parse_mode="HTML")
