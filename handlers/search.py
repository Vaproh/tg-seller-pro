from telegram import Update
from telegram.ext import ContextTypes
from core.permissions import require_seller
from core.state import state
from core.format import esc
from core.keyboards import search_type_keyboard
from database import search_accounts


async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not require_seller(update):
        return
    args = context.args
    if args:
        term = " ".join(args)
        results = search_accounts(term=term)
        if not results:
            await update.message.reply_text("No results found.")
            return
        text = f"<b>🔎 {len(results)} results for '{esc(term)}':</b>\n\n"
        for acc in results[:20]:
            text += (
                f"• #{acc['id']} | <code>{esc(acc['username'])}</code> | "
                f"{esc(dict(acc).get('category_name', '—'))} | {esc(dict(acc).get('status', 'active'))}\n"
            )
        await update.message.reply_text(text, parse_mode="HTML")
        return
    state.set(update.effective_user.id, "search_stage", "type")
    await update.message.reply_text("Select search type:", reply_markup=search_type_keyboard())


async def handle_search_type(update: Update, context: ContextTypes.DEFAULT_TYPE, search_type):
    user_id = update.effective_user.id
    state.set(user_id, "search_type", search_type)
    state.set(user_id, "search_stage", "value")
    labels = {
        "username": "username", "password": "password",
        "category": "category name", "status": "status",
        "buyer": "buyer name", "tag": "tag",
        "notes": "notes keyword", "general": "search term",
    }
    await update.callback_query.edit_message_text(f"Enter the {labels.get(search_type, 'value')}:")


async def handle_search_value(update: Update, context: ContextTypes.DEFAULT_TYPE, value):
    user_id = update.effective_user.id
    search_type = state.pop(user_id, "search_type", "general")
    state.pop(user_id, "search_stage")
    kwargs = {}
    if search_type == "username":
        kwargs["username"] = value
    elif search_type == "password":
        kwargs["password"] = value
    elif search_type == "category":
        kwargs["category"] = value
    elif search_type == "status":
        kwargs["status"] = value
    elif search_type == "notes":
        kwargs["notes_term"] = value
    else:
        kwargs["term"] = value
    results = search_accounts(**kwargs)
    if not results:
        await update.message.reply_text("No results found.")
        return
    text = f"<b>🔎 {len(results)} results:</b>\n\n"
    for acc in results[:20]:
        text += (
            f"• #{acc['id']} | <code>{esc(acc['username'])}</code> | "
            f"{esc(acc.get('category_name', '—'))} | {esc(acc.get('status', 'active'))}\n"
        )
    await update.message.reply_text(text, parse_mode="HTML")
