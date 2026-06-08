from telegram import Update
from telegram.ext import ContextTypes
from core.permissions import require_admin
from core.format import esc
from database import add_seller, remove_seller, list_sellers
from utils.notifications import notify_admin, fmt_seller_added, fmt_seller_removed


async def addseller_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not require_admin(update):
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /addseller <user_id> <name>")
        return
    try:
        user_id = int(args[0])
    except ValueError:
        await update.message.reply_text("Invalid user ID.")
        return
    name = " ".join(args[1:])
    success, msg = add_seller(user_id, name, update.effective_user.id)
    await update.message.reply_text(msg)
    if success:
        await notify_admin(context, fmt_seller_added(name, user_id))


async def removeseller_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not require_admin(update):
        return
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /removeseller <user_id>")
        return
    try:
        user_id = int(args[0])
    except ValueError:
        await update.message.reply_text("Invalid user ID.")
        return
    success = remove_seller(user_id)
    if success:
        await update.message.reply_text(f"Seller {user_id} removed.")
        await notify_admin(context, fmt_seller_removed("—", user_id))
    else:
        await update.message.reply_text("Seller not found.")


async def listsellers_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not require_admin(update):
        return
    sellers = list_sellers()
    if not sellers:
        await update.message.reply_text("No sellers registered.")
        return
    text = "<b>👥 Sellers</b>\n\n"
    for s in sellers:
        status = "🟢" if s["active"] else "🔴"
        text += (
            f"{status} {esc(s['name'])} (ID: {s['user_id']}) — "
            f"{s['sale_count']} sales, ₹{s['total_earnings']:.0f}\n"
        )
    await update.message.reply_text(text, parse_mode="HTML")
