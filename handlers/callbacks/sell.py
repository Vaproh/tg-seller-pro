from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.permissions import require_seller
from core.state import state
from core.format import esc, _d, fmt_receipt, _truncate
from core.keyboards import confirm_keyboard, sell_select_keyboard
from core.filters import (
    buyer_keyboard, apply_list_filters,
    fmt_account_list_line, PAGE_SIZE,
)
from database import (
    get_account_by_id, get_sale_by_id, sell_account, get_seller_by_user_id,
    get_buyer_names,
)
from database.sales import bulk_sell_accounts
from utils.notifications import notify_admin
import config


def _refresh_select_page(user_id, query):
    selected = state.get(user_id, "sell_selected", [])
    page = state.get(user_id, "sell_page", 1)
    filter_str = state.get(user_id, "sell_filter") or "status:available"
    accounts, total = apply_list_filters(filter_str, limit=PAGE_SIZE, offset=(page - 1) * PAGE_SIZE)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(1, min(page, total_pages))
    mode = state.get(user_id, "sell_mode", "bulk")
    max_select = 1 if mode == "single" else None
    return selected, accounts, page, total_pages, max_select, filter_str


async def try_handle(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str, user_id: int) -> bool:
    query = update.callback_query

    if data == "menu:sell":
        if not await require_seller(update):
            return True
        seller = get_seller_by_user_id(user_id)
        if not seller:
            await query.edit_message_text("⚠️ You are not registered as a seller.")
            return True
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("👆 Pick account", callback_data="sellmode:select"),
                InlineKeyboardButton("🎲 Pick any", callback_data="sellmode:any"),
            ],
        ])
        await query.edit_message_text("💰 Sell an account:", reply_markup=kb)
        return True

    if data.startswith("sellmode:"):
        if not await require_seller(update):
            return True
        mode = data.split(":", 1)[1]
        if mode == "select":
            state.set(user_id, "sell_mode", "single")
            state.set(user_id, "sell_selected", [])
            state.set(user_id, "sell_page", 1)
            accounts, total = apply_list_filters("status:available", limit=PAGE_SIZE, offset=0)
            total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
            text = f"<b>💰 Sell 1 Account — Tap to select</b>\n\n"
            for acc in accounts:
                text += fmt_account_list_line(acc) + "\n"
            kb = sell_select_keyboard([], accounts, 1, total_pages, max_select=1)
            await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        elif mode == "any":
            accounts, total = apply_list_filters("status:available", limit=1, offset=0)
            if not accounts:
                await query.edit_message_text("📭 No available accounts to sell.")
                return True
            acc = dict(accounts[0])
            state.set(user_id, "sell_mode", "single")
            state.set(user_id, "sell_selected", [acc["id"]])
            buyer_names = get_buyer_names()
            if buyer_names:
                kb = buyer_keyboard(buyer_names, "buypick")
                await query.edit_message_text(
                    f"🎲 Picked: #{acc['id']} — {esc(acc['username'])}\n\n👤 Select buyer or type a new one:",
                    reply_markup=kb,
                )
            else:
                state.set(user_id, "sell_stage", "buyer")
                await query.edit_message_text(
                    f"🎲 Picked: #{acc['id']} — {esc(acc['username'])}\n\n👤 Enter buyer name:"
                )
        return True

    if data.startswith("bulksellmode:"):
        if not await require_seller(update):
            return True
        mode = data.split(":", 1)[1]
        if mode == "select":
            state.set(user_id, "sell_mode", "bulk")
            state.set(user_id, "sell_selected", [])
            state.set(user_id, "sell_page", 1)
            accounts, total = apply_list_filters("status:available", limit=PAGE_SIZE, offset=0)
            total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
            text = f"<b>💰 Bulk Sell — Tap to select accounts</b>\n\n"
            for acc in accounts:
                text += fmt_account_list_line(acc) + "\n"
            kb = sell_select_keyboard([], accounts, 1, total_pages, max_select=None)
            await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        elif mode == "number":
            from database import count_accounts
            available = count_accounts(status="available")
            state.set(user_id, "sell_mode", "bulk")
            state.set(user_id, "sell_stage", "number")
            await query.edit_message_text(
                f"🔢 How many accounts to sell? (available: {available})"
            )
        return True

    if data.startswith("selltoggle:"):
        if not await require_seller(update):
            return True
        try:
            account_id = int(data.split(":")[1])
        except ValueError:
            return True
        selected = state.get(user_id, "sell_selected", [])
        mode = state.get(user_id, "sell_mode", "bulk")
        max_select = 1 if mode == "single" else None
        if account_id in selected:
            selected.remove(account_id)
        elif max_select and len(selected) >= max_select:
            await query.answer("⚠️ Max 1 account for single sell.", show_alert=True)
            return True
        else:
            selected.append(account_id)
        state.set(user_id, "sell_selected", selected)
        sel, accounts, page, total_pages, ms, fs = _refresh_select_page(user_id, query)
        title = "Sell 1 Account" if mode == "single" else "Bulk Sell"
        text = f"<b>💰 {title} — {len(sel)} selected</b>\n\n"
        for acc in accounts:
            text += fmt_account_list_line(acc) + "\n"
        kb = sell_select_keyboard(sel, accounts, page, total_pages, max_select=ms)
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return True

    if data.startswith("sellpage:"):
        if not await require_seller(update):
            return True
        try:
            page = int(data.split(":")[1])
        except ValueError:
            return True
        state.set(user_id, "sell_page", page)
        sel, accounts, page, total_pages, ms, fs = _refresh_select_page(user_id, query)
        mode = state.get(user_id, "sell_mode", "bulk")
        title = "Sell 1 Account" if mode == "single" else "Bulk Sell"
        text = f"<b>💰 {title} — {len(sel)} selected</b>\n\n"
        for acc in accounts:
            text += fmt_account_list_line(acc) + "\n"
        kb = sell_select_keyboard(sel, accounts, page, total_pages, max_select=ms)
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return True

    if data == "selldone":
        if not await require_seller(update):
            return True
        selected = state.get(user_id, "sell_selected", [])
        if not selected:
            await query.edit_message_text("⚠️ No accounts selected.")
            return True
        state.set(user_id, "sell_stage", "buyer")
        buyer_names = get_buyer_names()
        if buyer_names:
            kb = buyer_keyboard(buyer_names, "buypick")
            await query.edit_message_text(
                f"👤 {len(selected)} account(s) selected.\nSelect buyer:",
                reply_markup=kb,
            )
        else:
            await query.edit_message_text(f"👤 {len(selected)} account(s) selected.\nEnter buyer name:")
        return True

    if data.startswith("quicksell:"):
        if not await require_seller(update):
            return True
        try:
            account_id = int(data.split(":")[1])
        except ValueError:
            return True
        state.set(user_id, "sell_mode", "single")
        state.set(user_id, "sell_selected", [account_id])
        state.set(user_id, "sell_page", 1)
        buyer_names = get_buyer_names()
        if buyer_names:
            kb = buyer_keyboard(buyer_names, "buypick")
            account = get_account_by_id(account_id)
            a = _d(account) if account else {}
            await query.edit_message_text(
                f"💰 Selling: {esc(a.get('username', ''))}\n\n👤 Select buyer or type a new one:",
                reply_markup=kb,
            )
        else:
            state.set(user_id, "sell_stage", "buyer")
            await query.edit_message_text("👤 Enter buyer name:")
        return True

    if data.startswith("buypick:"):
        if not await require_seller(update):
            return True
        buyer_name = data.split(":", 1)[1]
        if buyer_name == "new":
            state.set(user_id, "sell_stage", "buyer")
            await query.edit_message_text("👤 Enter buyer name:")
            return True
        state.set(user_id, "sell_buyer", buyer_name)
        state.set(user_id, "sell_stage", "price")
        selected = state.get(user_id, "sell_selected", [])
        n = len(selected)
        label = f"{n} accounts" if n > 1 else "1 account"
        await query.edit_message_text(
            f"👤 Buyer: {esc(buyer_name)}\n\n💰 Enter price per account (₹):"
        )
        return True

    if data.startswith("paystatus:"):
        if not await require_seller(update):
            return True
        payment_status = data.split(":", 1)[1]
        state.set(user_id, "sell_payment_status", payment_status)
        selected = state.get(user_id, "sell_selected", [])
        buyer = state.get(user_id, "sell_buyer")
        price = state.get(user_id, "sell_price")
        mode = state.get(user_id, "sell_mode", "bulk")

        if mode == "single" and len(selected) == 1:
            account = get_account_by_id(selected[0])
            if not account:
                await query.edit_message_text("🔍 Account not found.")
                return True
            a = _d(account)
            ps_label = "🟡 Pending Payment" if payment_status == "pending" else "🟢 Sold"
            text_preview = (
                f"<b>Confirm Sale:</b>\n\n"
                f"Account: #{a['id']} — {esc(a['username'])}\n"
                f"Buyer: {esc(buyer)}\n"
                f"Price: ₹{price:.0f}\n"
                f"Status: {ps_label}\n\n"
                f"✅ Confirm?"
            )
        else:
            ps_label = "🟡 Pending Payment" if payment_status == "pending" else "🟢 Sold"
            text_preview = (
                f"<b>Confirm Bulk Sale:</b>\n\n"
                f"Accounts: {len(selected)}\n"
                f"Buyer: {esc(buyer)}\n"
                f"Price per account: ₹{price:.0f}\n"
                f"Status: {ps_label}\n\n"
                f"✅ Confirm?"
            )
        state.set(user_id, "sell_stage", "confirm")
        await query.edit_message_text(
            text_preview,
            parse_mode="HTML",
            reply_markup=confirm_keyboard("sellconfirm", "sellcancel"),
        )
        return True

    if data == "sellconfirm":
        if not await require_seller(update):
            return True
        seller = get_seller_by_user_id(user_id)
        if not seller:
            await query.edit_message_text("⚠️ You are not registered as a seller.")
            return True
        selected = state.pop(user_id, "sell_selected", [])
        buyer = state.pop(user_id, "sell_buyer")
        price = state.pop(user_id, "sell_price", 0)
        payment_status = state.pop(user_id, "sell_payment_status", "pending")
        mode = state.pop(user_id, "sell_mode", "bulk")
        state.pop(user_id, "sell_stage", None)
        state.pop(user_id, "sell_filter", None)
        state.pop(user_id, "sell_page", None)

        if not selected or not buyer:
            await query.edit_message_text("⚠️ Session expired. Please start over.")
            return True

        if mode == "single" and len(selected) == 1:
            account_id = selected[0]
            success, msg, sale_id = sell_account(
                account_id, seller["id"], buyer, price,
                payment_status=payment_status,
            )
            if success:
                sale = get_sale_by_id(sale_id)
                receipt = fmt_receipt(sale)
                await query.edit_message_text(receipt, parse_mode="HTML")
                status_label = "pending payment" if payment_status == "pending" else "sold"
                await notify_admin(context, f"💰 New sale! #{sale_id} — {buyer} — ₹{price:.0f} ({status_label}) — by {seller['name']}")
                if price >= config.HIGH_VALUE_THRESHOLD:
                    await notify_admin(context, f"🔥 High-value sale! #{sale_id} — ₹{price:.0f} from {buyer} — by {seller['name']}")
            else:
                await query.edit_message_text(f"❌ {msg}")
        else:
            result = bulk_sell_accounts(
                selected, seller["id"], buyer, price,
                payment_status=payment_status,
            )
            status_label = "pending payment" if payment_status == "pending" else "sold"
            await query.edit_message_text(
                f"✅ Bulk sell complete: {result['added']} {status_label}, {result['skipped']} skipped"
            )
            await notify_admin(context, f"💰 Bulk sell: {result['added']} accounts to {buyer} — ₹{price:.0f} each ({status_label}) — by {seller['name']}")
        return True

    if data == "sellcancel":
        for key in ("sell_selected", "sell_buyer", "sell_price", "sell_payment_status",
                     "sell_stage", "sell_filter", "sell_page", "sell_mode"):
            state.pop(user_id, key, None)
        await query.edit_message_text("❌ Sale cancelled.")
        return True

    return False
