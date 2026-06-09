from telegram import Update
from telegram.ext import ContextTypes
from core.permissions import require_admin, require_seller
from core.format import esc
from database import list_categories, add_category, delete_category
import config


async def categories_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    cats = list_categories()
    if not cats:
        await update.message.reply_text("📭 No categories found.")
        return
    text = "<b>📂 Categories</b>\n\n"
    for cat in cats:
        text += f"• {esc(cat['name'])} — {cat['account_count']} accounts — {config.CURRENCY}{cat['default_price']:.0f}\n"
    await update.message.reply_text(text, parse_mode="HTML")


async def addcategory_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    args = context.args
    if not args:
        await update.message.reply_text("📝 Usage: /addcategory <name>")
        return
    name = " ".join(args)
    success, msg = add_category(name)
    await update.message.reply_text(msg)


async def deletecategory_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    args = context.args
    if not args:
        await update.message.reply_text("📝 Usage: /deletecategory <name>")
        return
    name = " ".join(args)
    success, msg = delete_category(name)
    await update.message.reply_text(msg)
