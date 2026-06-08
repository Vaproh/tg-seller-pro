from telegram import Update
from telegram.ext import ContextTypes
from core.permissions import require_seller
from core.format import esc
from database import list_categories
import config


async def inventory_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    cats = list_categories()
    if not cats:
        await update.message.reply_text("📭 No categories found.")
        return
    from database.accounts import count_accounts
    from database.sales import count_sales, get_sales_summary
    total_available = count_accounts(status="active")
    total_sold = count_accounts(used=True)
    total_banned = count_accounts(status="banned")
    total_locked = count_accounts(status="locked")
    total_restricted = count_accounts(status="restricted")
    summary = get_sales_summary()
    text = "<b>📦 Inventory Overview</b>\n\n"
    text += f"🟢 Active: {total_available}\n"
    text += f"🔴 Sold: {total_sold}\n"
    text += f"⛔ Banned: {total_banned}\n"
    text += f"🔒 Locked: {total_locked}\n"
    text += f"⚠️ Restricted: {total_restricted}\n"
    text += f"💰 Total revenue: ₹{summary['total_revenue']:.0f}\n\n"
    text += "<b>By Category:</b>\n"
    for cat in cats:
        cat_available = count_accounts(category_id=cat["id"], status="active")
        cat_sold = count_accounts(category_id=cat["id"], used=True)
        text += f"• {esc(cat['name'])}: {cat_available} active, {cat_sold} sold\n"
    await update.message.reply_text(text, parse_mode="HTML")
