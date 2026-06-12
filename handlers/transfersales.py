from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.permissions import require_admin
from core.format import esc, code, _truncate
from database.sellers import list_sellers, get_seller_by_user_id
from database.sales import transfer_sales, count_sales
from core.state import state


async def transfersales_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    args = context.args
    if args and len(args) == 2:
        from_name = args[0].lstrip("@")
        to_name = args[1].lstrip("@")
        sellers = list_sellers()
        from_seller = None
        to_seller = None
        for s in sellers:
            sd = dict(s) if not isinstance(s, dict) else s
            if sd["name"].lower() == from_name.lower():
                from_seller = sd
            if sd["name"].lower() == to_name.lower():
                to_seller = sd
        if not from_seller:
            await update.message.reply_text(f"⚠️ Seller <code>{esc(from_name)}</code> not found.", parse_mode="HTML")
            return
        if not to_seller:
            await update.message.reply_text(f"⚠️ Seller <code>{esc(to_name)}</code> not found.", parse_mode="HTML")
            return
        if from_seller["id"] == to_seller["id"]:
            await update.message.reply_text("⚠️ Cannot transfer to the same seller.")
            return
        count = count_sales(seller_id=from_seller["id"])
        if count == 0:
            await update.message.reply_text(f"📭 <code>{esc(from_name)}</code> has no sales to transfer.", parse_mode="HTML")
            return
        user_id = update.effective_user.id
        state.set(user_id, "transfersales_from", from_seller)
        state.set(user_id, "transfersales_to", to_seller)
        state.set(user_id, "transfersales_count", count)
        text = (
            f"<b>🔄 Transfer Sales</b>\n\n"
            f"From: <code>{esc(from_name)}</code> ({count} sales)\n"
            f"To: <code>{esc(to_name)}</code>\n\n"
            f"Transfer all {count} sales from <code>{esc(from_name)}</code> to <code>{esc(to_name)}</code>?"
        )
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Confirm", callback_data="transfersales:confirm"),
                InlineKeyboardButton("❌ Cancel", callback_data="transfersales:cancel"),
            ]
        ])
        await update.message.reply_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return
    sellers = list_sellers()
    if not sellers:
        await update.message.reply_text("📭 No sellers found.")
        return
    buttons = []
    for s in sellers:
        sd = dict(s) if not isinstance(s, dict) else s
        buttons.append([
            InlineKeyboardButton(
                f"{esc(sd['name'])}",
                callback_data=f"transfersalespick:{sd['id']}",
            )
        ])
    user_id = update.effective_user.id
    state.set(user_id, "transfersales_step", "from")
    await update.message.reply_text(
        "🔄 <b>Transfer Sales</b>\n\nSelect the seller to transfer FROM:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
