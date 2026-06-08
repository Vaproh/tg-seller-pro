from telegram import Update
from telegram.ext import ContextTypes
from core.permissions import require_admin
from core.keyboards import report_period_keyboard
from database import get_sales_summary, list_categories
from database.sellers import list_sellers
from database.accounts import count_accounts


async def report_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    await update.message.reply_text("📊 Select a period:", reply_markup=report_period_keyboard())


async def handle_report_period(update: Update, context: ContextTypes.DEFAULT_TYPE, period):
    query = update.callback_query
    await query.answer()
    summary = get_sales_summary(period=period)
    total = get_sales_summary()
    sellers = list_sellers()
    cats = list_categories()
    available = count_accounts(status="active")
    sold = count_accounts(used=True)
    period_labels = {"today": "Today", "week": "This Week", "month": "This Month", "all": "All Time"}
    label = period_labels.get(period, period)
    text = f"<b>📊 Report — {label}</b>\n\n"
    text += f"💰 Revenue: ₹{summary['total_revenue']:.0f}\n"
    text += f"📈 Sales: {summary['total_sales']}\n"
    text += f"💳 Pending: {summary['pending_count']} (₹{summary['pending_amount']:.0f})\n"
    text += f"📦 Inventory: {available} available, {sold} sold\n\n"
    text += "<b>By Seller:</b>\n"
    has_seller_sales = False
    for s in sellers:
        if s["sale_count"] > 0:
            text += f"• {s['name']}: {s['sale_count']} sales, ₹{s['total_earnings']:.0f}\n"
            has_seller_sales = True
    if not has_seller_sales:
        text += "• No sales yet\n"
    text += "\n<b>By Category:</b>\n"
    for cat in cats:
        text += f"• {cat['name']}: {cat['account_count']} accounts\n"
    text += f"\n<b>All-Time Total:</b> ₹{total['total_revenue']:.0f}"
    await query.edit_message_text(text, parse_mode="HTML")
