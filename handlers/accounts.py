import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.permissions import require_admin, require_seller
from core.state import state
from core.format import esc, fmt_account_block, _d, _truncate
from core.keyboards import category_keyboard, confirm_keyboard
from core.filters import (
    filter_page_keyboard, apply_list_filters, count_from_filter,
    fmt_account_list_page, parse_id_list, PAGE_SIZE,
)
from database import (
    add_account, add_accounts_bulk, get_account_by_id,
    list_accounts, count_accounts, delete_account, delete_accounts_by_ids,
    export_accounts_csv, list_categories, get_category_name,
)
from utils.parsers import parse_bulk_lines
from utils.notifications import notify_admin, fmt_bulk_import
import config

logger = logging.getLogger(__name__)


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
    if args:
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
            f"⚠️ Delete account #{account_id} ({esc(_d(account)['username'])})?",
            reply_markup=confirm_keyboard(f"delconfirm:{account_id}", "delcancel"),
        )
        return
    state.set(update.effective_user.id, "delete_filter", None)
    state.set(update.effective_user.id, "delete_page", 1)
    accounts, total = apply_list_filters(None, limit=PAGE_SIZE, offset=0)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    text = fmt_account_list_page(accounts, 1, total_pages, title="Delete Accounts")
    kb = filter_page_keyboard(
        "delfilter", 1, total_pages,
        include_all=True, include_available=True, include_sold=True,
        include_pending=True, include_ids=True,
    )
    await update.message.reply_text(_truncate(text), parse_mode="HTML", reply_markup=kb)


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
    user_id = update.effective_user.id
    state.set(user_id, "list_filter", None)
    state.set(user_id, "list_page", 1)
    accounts, total = apply_list_filters(None, limit=PAGE_SIZE, offset=0)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    text = fmt_account_list_page(accounts, 1, total_pages, title="Accounts")
    kb = filter_page_keyboard(
        "listfilter", 1, total_pages,
        include_all=True, include_available=True, include_sold=True,
        include_pending=True, include_ids=True,
    )
    await update.message.reply_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
