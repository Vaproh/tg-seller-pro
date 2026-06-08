import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.permissions import require_admin, require_seller
from core.state import state
from core.format import esc, fmt_account_block, fmt_compact
from core.keyboards import category_keyboard, confirm_keyboard, pagination_keyboard
from database import (
    add_account, add_accounts_bulk, get_account_by_id,
    list_accounts, count_accounts, delete_account, delete_accounts_by_ids,
    export_accounts_csv, list_categories, get_category_name,
)
from utils.parsers import parse_bulk_lines
from utils.notifications import notify_admin, fmt_bulk_import
import config

logger = logging.getLogger(__name__)

PAGE_SIZE = 10


async def add_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    state.set(update.effective_user.id, "add_stage", "username")
    await update.message.reply_text("👤 Send the Reddit username:")


async def add_bulk_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    kb = category_keyboard("bulkcat")
    if not kb:
        await update.message.reply_text("📂 No categories. Create one first with /addcategory")
        return
    await update.message.reply_text("📂 Select a category for bulk import:", reply_markup=kb)
    state.set(update.effective_user.id, "bulk_stage", "category")


async def getid_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    args = context.args
    if not args:
        await update.message.reply_text("📝 Usage: /getid <account_id>")
        return
    try:
        account_id = int(args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Invalid ID.")
        return
    account = get_account_by_id(account_id)
    if not account:
        await update.message.reply_text("🔍 Account not found.")
        return
    await update.message.reply_text(fmt_account_block(account), parse_mode="HTML")


async def delete_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    args = context.args
    if not args:
        await update.message.reply_text("📝 Usage: /delete <account_id>")
        return
    try:
        account_id = int(args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Invalid ID.")
        return
    account = get_account_by_id(account_id)
    if not account:
        await update.message.reply_text("🔍 Account not found.")
        return
    state.set(update.effective_user.id, "delete_confirm", account_id)
    await update.message.reply_text(
        f"⚠️ Delete account #{account_id} ({esc(account['username'])})?",
        reply_markup=confirm_keyboard(f"delconfirm:{account_id}", "delcancel"),
    )


async def bulkdelete_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    state.set(update.effective_user.id, "bulk_delete_mode", "input")
    await update.message.reply_text(
        "🗑️ Enter account IDs (comma-separated) or a category name to delete all in that category:"
    )


async def extractcsv_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    kb = category_keyboard("csvcat")
    if not kb:
        await update.message.reply_text("📂 No categories. Create one first with /addcategory")
        return
    await update.message.reply_text("📂 Select a category for CSV import:", reply_markup=kb)
    state.set(update.effective_user.id, "csv_stage", "category")


async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    state.set(update.effective_user.id, "list_page", 1)
    state.set(update.effective_user.id, "list_filter", None)
    total = count_accounts()
    if total == 0:
        await update.message.reply_text("📭 No accounts found.")
        return
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    accounts = list_accounts(limit=PAGE_SIZE, offset=0)
    text = f"<b>📋 Accounts (1/{total_pages})</b>\n\n"
    for acc in accounts:
        text += fmt_compact(acc) + "\n"
    kb = pagination_keyboard("accountpage", 1, total_pages)
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)
