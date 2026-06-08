import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.permissions import require_seller, require_admin, get_user_role
from core.state import state
from core.format import esc, fmt_sale_block, fmt_receipt
from core.keyboards import (
    sell_accounts_keyboard, sale_status_keyboard,
    pagination_keyboard, confirm_keyboard,
)
from database import (
    sell_account, bulk_sell_accounts, mark_payment, get_sales, count_sales,
    get_sale_by_id, void_sale, list_accounts, count_accounts, get_category_name,
    get_seller_by_user_id,
)
from utils.notifications import (
    notify_admin, fmt_sale_notification, fmt_payment_notification,
    fmt_high_value_notification, fmt_void_notification,
)
import config

logger = logging.getLogger(__name__)

PAGE_SIZE = 10


async def sell_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    user_id = update.effective_user.id
    seller = get_seller_by_user_id(user_id)
    if not seller:
        await update.message.reply_text("⚠️ You are not registered as a seller.")
        return
    accounts = list_accounts(limit=20, status="active")
    if not accounts:
        await update.message.reply_text("📭 No available accounts to sell.")
        return
    state.set(user_id, "sell_stage", "select_account")
    kb = sell_accounts_keyboard(accounts, "sellselect")
    await update.message.reply_text("💰 Select an account to sell:", reply_markup=kb)


async def bulksell_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    user_id = update.effective_user.id
    seller = get_seller_by_user_id(user_id)
    if not seller:
        await update.message.reply_text("⚠️ You are not registered as a seller.")
        return
    state.set(user_id, "bulksell_stage", "buyer")
    await update.message.reply_text("👤 Enter the buyer name:")


async def sales_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    seller = get_seller_by_user_id(user_id) if role != "admin" else None
    seller_id = seller["id"] if seller else None
    state.set(user_id, "sales_page", 1)
    state.set(user_id, "sales_filter", None)
    total = count_sales(seller_id=seller_id)
    if total == 0:
        await update.message.reply_text("📭 No sales found.")
        return
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    sales = get_sales(limit=PAGE_SIZE, offset=0, seller_id=seller_id)
    text = f"<b>📈 Sales (1/{total_pages})</b>\n\n"
    for s in sales:
        text += (
            f"• #{s['id']} | {esc(s['buyer_name'])} | "
            f"₹{s['price']:.0f} | {esc(s['payment_status'])} | "
            f"{esc(dict(s).get('seller_name', '—'))}\n"
        )
    kb = pagination_keyboard("salespage", 1, total_pages)
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)


async def sale_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    args = context.args
    if not args:
        await update.message.reply_text("📝 Usage: /sale <sale_id>")
        return
    try:
        sale_id = int(args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Invalid sale ID.")
        return
    sale = get_sale_by_id(sale_id)
    if not sale:
        await update.message.reply_text("🔍 Sale not found.")
        return
    await update.message.reply_text(fmt_sale_block(sale), parse_mode="HTML")


async def markpaid_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    seller = get_seller_by_user_id(user_id) if role != "admin" else None
    seller_id = seller["id"] if seller else None
    pending = get_sales(limit=20, seller_id=seller_id, status="pending")
    if not pending:
        await update.message.reply_text("📭 No pending payments.")
        return
    buttons = []
    for s in pending:
        buttons.append([
            InlineKeyboardButton(
                f"#{s['id']} | {s['buyer_name']} | ₹{s['price']:.0f}",
                callback_data=f"markpaid:{s['id']}",
            )
        ])
    kb = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("💳 Select a sale to mark as paid:", reply_markup=kb)


async def voidsale_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    args = context.args
    if not args:
        await update.message.reply_text("📝 Usage: /voidsale <sale_id>")
        return
    try:
        sale_id = int(args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Invalid sale ID.")
        return
    sale = get_sale_by_id(sale_id)
    if not sale:
        await update.message.reply_text("🔍 Sale not found.")
        return
    state.set(update.effective_user.id, "void_confirm", sale_id)
    await update.message.reply_text(
        f"⚠️ Void sale #{sale_id}? Account will return to stock.",
        reply_markup=confirm_keyboard(f"voidconfirm:{sale_id}", "voidcancel"),
    )
