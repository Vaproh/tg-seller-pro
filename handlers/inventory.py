from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.permissions import require_seller
from core.format import esc
from core.filters import (
    filter_page_keyboard, apply_list_filters, count_from_filter,
    fmt_account_list_page, parse_filter_state, build_filter_state, PAGE_SIZE,
)
from database import list_categories, count_accounts, get_category_name
from database.sales import get_sales_summary
import config


async def inventory_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    user_id = update.effective_user.id
    from core.state import state
    state.set(user_id, "inv_filter", None)
    state.set(user_id, "inv_page", 1)
    cats = list_categories()
    if not cats:
        await update.message.reply_text("📭 No categories found.")
        return
    available = count_accounts(status="available")
    sold = count_accounts(status="sold")
    pending = count_accounts(status="pending_payment")
    summary = get_sales_summary()
    text = "<b>📦 Inventory Overview</b>\n\n"
    text += f"🟢 Available: {available}\n"
    text += f"🔴 Sold: {sold}\n"
    text += f"🟡 Pending Payment: {pending}\n"
    text += f"💰 Total revenue: ₹{summary.get('total_revenue', 0):.0f}\n"
    text += f"💳 Pending: ₹{summary.get('pending_amount', 0):.0f}\n\n"
    text += "<b>📂 By Category:</b>\n"
    for cat in cats:
        cat_avail = count_accounts(category_id=cat["id"], status="available")
        cat_sold = count_accounts(category_id=cat["id"], status="sold")
        cat_pend = count_accounts(category_id=cat["id"], status="pending_payment")
        text += f"• {esc(cat['name'])}: 🟢{cat_avail} 🔴{cat_sold} 🟡{cat_pend}\n"
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟢 Available", callback_data="invfilter:available"),
            InlineKeyboardButton("🔴 Sold", callback_data="invfilter:sold"),
        ],
        [
            InlineKeyboardButton("🟡 Pending", callback_data="invfilter:pending_payment"),
            InlineKeyboardButton("📋 All", callback_data="invfilter:all"),
        ],
        [
            InlineKeyboardButton("📂 By Category", callback_data="invfiltercat"),
        ],
    ])
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)
