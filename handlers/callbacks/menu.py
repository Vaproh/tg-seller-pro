from telegram import Update
from telegram.ext import ContextTypes
from core.permissions import get_user_role
from core.keyboards import main_menu_keyboard


async def try_handle(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str, user_id: int) -> bool:
    query = update.callback_query

    if data == "menu:back":
        role = get_user_role(user_id)
        is_admin = role == "admin"
        kb = main_menu_keyboard(is_admin=is_admin)
        await query.edit_message_text("📋 Main Menu", reply_markup=kb)
        return True

    return False
