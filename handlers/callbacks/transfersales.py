import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.permissions import require_admin
from core.format import esc, code, _truncate
from core.state import state
from database.sellers import list_sellers
from database.sales import transfer_sales, count_sales

logger = logging.getLogger(__name__)


async def handle_transfersales_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str, user_id: int) -> bool:
    query = update.callback_query
    await query.answer()

    if data == "transfersales:confirm":
        from_seller = state.get(user_id, "transfersales_from")
        to_seller = state.get(user_id, "transfersales_to")
        count = state.get(user_id, "transfersales_count")
        if not from_seller or not to_seller or count is None:
            await query.edit_message_text("⚠️ Session expired. Please start again.")
            return True
        transferred = transfer_sales(from_seller["id"], to_seller["id"])
        for key in ("transfersales_from", "transfersales_to", "transfersales_count", "transfersales_step"):
            state.pop(user_id, key, None)
        text = (
            f"✅ <b>Transfer Complete</b>\n\n"
            f"Transferred {transferred} sales from "
            f"<code>{esc(from_seller['name'])}</code> to "
            f"<code>{esc(to_seller['name'])}</code>"
        )
        await query.edit_message_text(_truncate(text), parse_mode="HTML")
        return True

    if data == "transfersales:cancel":
        for key in ("transfersales_from", "transfersales_to", "transfersales_count", "transfersales_step"):
            state.pop(user_id, key, None)
        await query.edit_message_text("❌ Transfer cancelled.")
        return True

    if data.startswith("transfersalespick:"):
        seller_id = int(data.split(":")[1])
        sellers = list_sellers()
        picked = None
        for s in sellers:
            sd = dict(s) if not isinstance(s, dict) else s
            if sd["id"] == seller_id:
                picked = sd
                break
        if not picked:
            await query.edit_message_text("⚠️ Seller not found.")
            return True

        step = state.get(user_id, "transfersales_step")
        if step == "from":
            state.set(user_id, "transfersales_from", picked)
            state.set(user_id, "transfersales_step", "to")
            buttons = []
            for s in sellers:
                sd = dict(s) if not isinstance(s, dict) else s
                if sd["id"] != seller_id:
                    buttons.append([
                        InlineKeyboardButton(
                            f"{esc(sd['name'])}",
                            callback_data=f"transfersalespick:{sd['id']}",
                        )
                    ])
            if not buttons:
                await query.edit_message_text("⚠️ No other sellers to transfer to.")
                return True
            await query.edit_message_text(
                f"🔄 <b>Transfer Sales</b>\n\n"
                f"From: <code>{esc(picked['name'])}</code>\n\n"
                f"Select the seller to transfer TO:",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
            return True

        if step == "to":
            from_seller = state.get(user_id, "transfersales_from")
            if not from_seller:
                await query.edit_message_text("⚠️ Session expired. Please start again.")
                return True
            if from_seller["id"] == picked["id"]:
                await query.edit_message_text("⚠️ Cannot transfer to the same seller.")
                return True
            count = count_sales(seller_id=from_seller["id"])
            if count == 0:
                for key in ("transfersales_from", "transfersales_to", "transfersales_step", "transfersales_count"):
                    state.pop(user_id, key, None)
                await query.edit_message_text(f"📭 <code>{esc(from_seller['name'])}</code> has no sales to transfer.", parse_mode="HTML")
                return True
            state.set(user_id, "transfersales_to", picked)
            state.set(user_id, "transfersales_count", count)
            text = (
                f"<b>🔄 Transfer Sales</b>\n\n"
                f"From: <code>{esc(from_seller['name'])}</code> ({count} sales)\n"
                f"To: <code>{esc(picked['name'])}</code>\n\n"
                f"Transfer all {count} sales?"
            )
            kb = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Confirm", callback_data="transfersales:confirm"),
                    InlineKeyboardButton("❌ Cancel", callback_data="transfersales:cancel"),
                ]
            ])
            await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
            return True

    return False
