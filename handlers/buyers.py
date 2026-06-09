from telegram import Update
from telegram.ext import ContextTypes
from core.permissions import require_seller, get_user_role
from core.format import esc, code, code_id
from core.state import state
from database import get_buyers, get_buyer_sales
from database.sellers import get_seller_by_user_id


async def buyers_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    seller = get_seller_by_user_id(user_id) if role != "admin" else None
    seller_id = seller["id"] if seller else None
    buyers = get_buyers(seller_id=seller_id)
    if not buyers:
        await update.message.reply_text("📭 No buyers found.")
        return
    text = "<b>👥 Buyers</b>\n\n"
    for b in buyers:
        text += (
            f"• {esc(b['buyer_name'])} — {b['total_sales']} purchases — "
            f"₹{b['total_spent']:.0f} total"
        )
        if b['pending_amount'] > 0:
            text += f" (₹{b['pending_amount']:.0f} pending)"
        text += "\n"
    await update.message.reply_text(text, parse_mode="HTML")


async def buyer_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    args = context.args
    if not args:
        await update.message.reply_text("📝 Usage: /buyer <name>")
        return
    buyer_name = " ".join(args)
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    seller = get_seller_by_user_id(user_id) if role != "admin" else None
    seller_id = seller["id"] if seller else None
    sales = get_buyer_sales(buyer_name, seller_id=seller_id)
    if not sales:
        await update.message.reply_text(f"📭 No purchases found for '{code(buyer_name)}'.")
        return
    text = f"<b>👤 Buyer: {code(buyer_name)}</b>\n\n"
    for s in sales:
        text += (
            f"• {code_id(s['id'])} | {esc(dict(s).get('category_name', '—'))} | "
            f"₹{s['price']:.0f} | {esc(s['payment_status'])} | "
            f"{esc(s['sold_at'][:10])}\n"
        )
    await update.message.reply_text(text, parse_mode="HTML")
