from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.permissions import require_seller
from core.state import state
from core.format import esc, reddit_url, _d, code_id, code_username, code
from core.keyboards import category_keyboard
from database import get_available_accounts_for_category, list_accounts, get_category_name


async def preview_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    kb = category_keyboard("previewcat", include_all=True)
    if not kb:
        await update.message.reply_text("📭 No categories found.")
        return
    await update.message.reply_text("📂 Select a category:", reply_markup=kb)


async def handle_preview_category(update: Update, context: ContextTypes.DEFAULT_TYPE, cat_id_str):
    query = update.callback_query
    await query.answer()
    if cat_id_str == "all":
        state.set(query.from_user.id, "preview_category", "all")
        state.set(query.from_user.id, "preview_stage", "count")
        await query.edit_message_text("🔢 How many accounts to pull?")
        return
    try:
        cat_id = int(cat_id_str)
    except ValueError:
        return
    cat_name = get_category_name(cat_id)
    if not cat_name:
        await query.edit_message_text("🔍 Category not found.")
        return
    state.set(query.from_user.id, "preview_category", cat_id)
    state.set(query.from_user.id, "preview_stage", "count")
    await query.edit_message_text(f"📂 Category: {code(cat_name)}\n🔢 How many accounts to pull?", parse_mode="HTML")


async def handle_preview_count(update: Update, context: ContextTypes.DEFAULT_TYPE, count_str):
    user_id = update.effective_user.id
    try:
        count = int(count_str)
        if count <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ Enter a positive number:")
        return
    cat_id = state.get(user_id, "preview_category")
    if cat_id == "all":
        accounts = list_accounts(limit=count, status="available")
    else:
        accounts = get_available_accounts_for_category(cat_id, limit=count)
    state.pop(user_id, "preview_stage")
    state.pop(user_id, "preview_category")
    if not accounts:
        await update.message.reply_text("📭 No available accounts.")
        return
    text = f"<b>📂 {len(accounts)} accounts:</b>\n\n"
    buttons = []
    for acc in accounts:
        a = _d(acc)
        text += (
            f"• {code_id(a.get('id', ''))} | {code_username(a.get('username'))}\n"
            f"  🔗 {code(reddit_url(a.get('username', '')))}\n"
        )
        buttons.append([
            InlineKeyboardButton(
                f"💰 Sell {code_id(a['id'])} ({code_username(a['username'])})",
                callback_data=f"quicksell:{a['id']}",
            )
        ])
    kb = InlineKeyboardMarkup(buttons) if buttons else None
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)
