from telegram import Update
from telegram.ext import ContextTypes
from core.permissions import require_seller, get_user_role
from core.keyboards import main_menu_keyboard, add_menu_keyboard, settings_keyboard
from core.help_content import HELP_MAIN_ADMIN, HELP_MAIN_SELLER
import config


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not require_seller(update):
        return
    role = get_user_role(update.effective_user.id)
    is_admin = role == "admin"
    keyboard = main_menu_keyboard(is_admin=is_admin)
    text = HELP_MAIN_ADMIN if is_admin else HELP_MAIN_SELLER
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)


async def mainmenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not require_seller(update):
        return
    role = get_user_role(update.effective_user.id)
    is_admin = role == "admin"
    keyboard = main_menu_keyboard(is_admin=is_admin)
    await update.message.reply_text("📋 Main Menu", reply_markup=keyboard)


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not require_seller(update):
        return
    await update.message.reply_text("pong")
