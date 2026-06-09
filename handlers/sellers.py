from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.permissions import require_admin
from core.format import esc, code_id
from database import add_seller, remove_seller, list_sellers
from database.sellers import get_seller_by_user_id
from utils.notifications import notify_admin, fmt_seller_added, fmt_seller_removed
import config


async def addseller_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("📝 Usage: /addseller <user_id> <name>")
        return
    try:
        user_id = int(args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Invalid user ID.")
        return
    name = " ".join(args[1:])
    success, msg = add_seller(user_id, name, update.effective_user.id)
    await update.message.reply_text(msg)
    if success:
        await notify_admin(context, fmt_seller_added(name, user_id))


async def removeseller_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    args = context.args
    if not args:
        await update.message.reply_text("📝 Usage: /removeseller <user_id>")
        return
    try:
        user_id = int(args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Invalid user ID.")
        return
    seller = get_seller_by_user_id(user_id)
    seller_name = esc(seller["name"]) if seller else "—"
    success = remove_seller(user_id)
    if success:
        await update.message.reply_text(
            f"✅ Seller {code_id(user_id)} removed.",
            parse_mode="HTML",
        )
        await notify_admin(context, fmt_seller_removed(seller_name, user_id))
    else:
        await update.message.reply_text("🔍 Seller not found.")


async def listsellers_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    sellers = list_sellers()
    if not sellers:
        await update.message.reply_text("📭 No sellers registered.")
        return
    text = "<b>👥 Sellers</b>\n\n"
    for s in sellers:
        status = "🟢" if s["active"] else "🔴"
        text += (
            f"{status} {esc(s['name'])} — ID: {code_id(s['user_id'])}\n"
            f"   📊 {s['sale_count']} sales — {config.CURRENCY}{s['total_earnings']:.0f}\n"
        )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back", callback_data="menu:back")],
    ])
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)
