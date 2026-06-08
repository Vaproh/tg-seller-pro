from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.permissions import require_seller
from core.state import state
from core.format import esc, _d, _truncate
from core.filters import (
    filter_page_keyboard, fmt_account_list_line, fmt_account_list_page,
    parse_filter_state, build_filter_state, PAGE_SIZE, MAX_MSG_LEN,
)
from database import search_accounts, list_categories, count_accounts
import config


async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    args = context.args
    if args:
        term = " ".join(args)
        results = search_accounts(term=term)
        if not results:
            await update.message.reply_text("📭 No results found.")
            return
        text = _fmt_search_results(results[:20], term)
        await update.message.reply_text(_truncate(text), parse_mode="HTML")
        return
    state.set(update.effective_user.id, "search_stage", "type")
    kb = _search_type_keyboard()
    await update.message.reply_text("🔎 Select search type:", reply_markup=kb)


async def handle_search_type(update: Update, context: ContextTypes.DEFAULT_TYPE, search_type):
    user_id = update.effective_user.id
    query = update.callback_query
    state.set(user_id, "search_type", search_type)

    if search_type == "category":
        cats = list_categories()
        if not cats:
            await query.edit_message_text("📭 No categories found.")
            return
        buttons = []
        for cat in cats:
            buttons.append([
                InlineKeyboardButton(
                    f"📂 {cat['name']} ({cat['account_count']})",
                    callback_data=f"searchcat:{cat['id']}",
                )
            ])
        buttons.append([InlineKeyboardButton("📋 All", callback_data="searchcat:all")])
        await query.edit_message_text("📂 Select category:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if search_type == "status":
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🟢 Available", callback_data="searchstatus:available"),
                InlineKeyboardButton("🔴 Sold", callback_data="searchstatus:sold"),
            ],
            [
                InlineKeyboardButton("🟡 Pending", callback_data="searchstatus:pending_payment"),
            ],
        ])
        await query.edit_message_text("📊 Select status:", reply_markup=kb)
        return

    if search_type == "id":
        state.set(user_id, "search_stage", "value")
        await query.edit_message_text(
            "🔢 Enter account ID(s) (comma-separated for multiple):"
        )
        return

    labels = {
        "username": "Reddit username",
        "password": "password",
        "buyer": "buyer name",
        "tag": "tag",
        "notes": "notes keyword",
        "general": "search term",
    }
    state.set(user_id, "search_stage", "value")
    await query.edit_message_text(f"📝 Enter the {labels.get(search_type, 'value')}:")


async def handle_search_value(update: Update, context: ContextTypes.DEFAULT_TYPE, value):
    user_id = update.effective_user.id
    search_type = state.pop(user_id, "search_type", "general")
    state.pop(user_id, "search_stage")

    if search_type == "id":
        ids = []
        for part in value.replace(" ", ",").split(","):
            part = part.strip()
            if part.isdigit():
                ids.append(int(part))
        if not ids:
            await update.message.reply_text("⚠️ No valid IDs provided.")
            return
        results = search_accounts(id_list=ids)
        if not results:
            await update.message.reply_text("📭 No accounts found with those IDs.")
            return
        text = f"<b>🔢 Search Results ({len(results)} accounts):</b>\n\n"
        for acc in results:
            text += fmt_account_list_line(acc) + "\n"
        await update.message.reply_text(_truncate(text), parse_mode="HTML")
        return

    kwargs = {}
    if search_type == "username":
        kwargs["username"] = value
    elif search_type == "password":
        kwargs["password"] = value
    elif search_type == "buyer":
        kwargs["buyer"] = value
    elif search_type == "tag":
        kwargs["tag"] = value
    elif search_type == "notes":
        kwargs["notes_term"] = value
    else:
        kwargs["term"] = value

    results = search_accounts(**kwargs)
    if not results:
        await update.message.reply_text("📭 No results found.")
        return
    text = f"<b>🔎 {len(results)} results:</b>\n\n"
    for acc in results[:20]:
        text += fmt_account_list_line(acc) + "\n"
    await update.message.reply_text(_truncate(text), parse_mode="HTML")


async def handle_search_category(update: Update, context: ContextTypes.DEFAULT_TYPE, cat_id_str):
    user_id = update.effective_user.id
    query = update.callback_query
    if cat_id_str == "all":
        results = search_accounts()
    else:
        try:
            cat_id = int(cat_id_str)
        except ValueError:
            return
        results = search_accounts(category_id=cat_id)
    if not results:
        await query.edit_message_text("📭 No accounts found.")
        return
    text = f"<b>📂 Search Results ({len(results)} accounts):</b>\n\n"
    for acc in results[:20]:
        text += fmt_account_list_line(acc) + "\n"
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔎 Search Again", callback_data="menu:search"),
        InlineKeyboardButton("⬅️ Back", callback_data="menu:back"),
    ]])
    await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)


async def handle_search_status(update: Update, context: ContextTypes.DEFAULT_TYPE, status_val):
    user_id = update.effective_user.id
    query = update.callback_query
    results = search_accounts(status=status_val)
    if not results:
        await query.edit_message_text("📭 No accounts found with that status.")
        return
    text = f"<b>📊 {status_val.upper()} Accounts ({len(results)} total):</b>\n\n"
    for acc in results[:2]:
        text += fmt_account_list_line(acc) + "\n"
    if len(results) > 2:
        text += f"\n... and {len(results) - 2} more"
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔎 Search Again", callback_data="menu:search"),
        InlineKeyboardButton("⬅️ Back", callback_data="menu:back"),
    ]])
    await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)


def _search_type_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👤 Username", callback_data="search:username"),
            InlineKeyboardButton("🔑 Password", callback_data="search:password"),
        ],
        [
            InlineKeyboardButton("📂 Category", callback_data="search:category"),
            InlineKeyboardButton("📊 Status", callback_data="search:status"),
        ],
        [
            InlineKeyboardButton("👤 Buyer", callback_data="search:buyer"),
            InlineKeyboardButton("🏷️ Tag", callback_data="search:tag"),
        ],
        [
            InlineKeyboardButton("📝 Notes", callback_data="search:notes"),
            InlineKeyboardButton("🔍 General", callback_data="search:general"),
        ],
        [
            InlineKeyboardButton("🔢 By ID", callback_data="search:id"),
        ],
    ])


def _fmt_search_results(results, query_term=""):
    text = f"<b>🔎 {len(results)} results for '{esc(query_term)}':</b>\n\n"
    for acc in results:
        text += fmt_account_list_line(acc) + "\n"
    return text
