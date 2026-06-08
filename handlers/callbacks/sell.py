from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.permissions import require_seller
from core.state import state
from core.format import esc, _d, fmt_receipt, _truncate
from core.keyboards import confirm_keyboard, category_keyboard
from core.filters import (
    buyer_keyboard, payment_status_keyboard,
    filter_page_keyboard, apply_list_filters, fmt_account_list_page,
    parse_filter_state, build_filter_state, parse_id_list,
    fmt_account_list_line, category_keyboard_with_all, PAGE_SIZE,
)
from database import (
    list_categories, get_category_name, count_accounts,
    get_account_by_id, get_sale_by_id, sell_account, get_seller_by_user_id,
    get_buyer_names,
)
from database.sales import bulk_sell_accounts
from utils.notifications import notify_admin
import config


def _bulksell_select_keyboard(selected, accounts, page, total_pages):
    buttons = []
    for acc in accounts:
        a = _d(acc)
        mark = "✅" if a["id"] in selected else "  "
        buttons.append([
            InlineKeyboardButton(
                f"{mark} #{a['id']} | {esc(a['username'])}",
                callback_data=f"bulkseltoggle:{a['id']}",
            )
        ])
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"bulkselpage:{page - 1}"))
    nav_row.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("➡️", callback_data=f"bulkselpage:{page + 1}"))
    buttons.append(nav_row)
    buttons.append([
        InlineKeyboardButton(
            f"✅ Done ({len(selected)} selected)",
            callback_data="bulkselldone",
        ),
        InlineKeyboardButton("❌ Cancel", callback_data="bulksellcancel"),
    ])
    return InlineKeyboardMarkup(buttons)


async def try_handle(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str, user_id: int) -> bool:
    query = update.callback_query

    if data == "menu:sell":
        if not await require_seller(update):
            return True
        seller = get_seller_by_user_id(user_id)
        if not seller:
            await query.edit_message_text("⚠️ You are not registered as a seller.")
            return True
        state.set(user_id, "sell_filter", "status:available")
        state.set(user_id, "sell_page", 1)
        accounts, total = apply_list_filters("status:available", limit=PAGE_SIZE, offset=0)
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        text = fmt_account_list_page(accounts, 1, total_pages, title="Available Accounts to Sell")
        kb = filter_page_keyboard(
            "sellfilter", 1, total_pages,
            include_available=True, include_sold=False, include_pending=False,
            include_all=False, include_ids=True,
        )
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return True

    if data.startswith("sellfilter:") and not data.startswith("sellfiltercat") and not data.startswith("sellfilterids"):
        if not await require_seller(update):
            return True
        f = data.split(":", 1)[1]
        if f == "all":
            state.set(user_id, "sell_filter", "status:available")
        else:
            state.set(user_id, "sell_filter", f"status:{f}")
        state.set(user_id, "sell_page", 1)
        filter_str = state.get(user_id, "sell_filter")
        accounts, total = apply_list_filters(filter_str, limit=PAGE_SIZE, offset=0)
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        text = fmt_account_list_page(accounts, 1, total_pages, title="Available Accounts to Sell")
        kb = filter_page_keyboard(
            "sellfilter", 1, total_pages,
            include_available=True, include_sold=False, include_pending=False,
            include_all=False, include_ids=True,
        )
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return True

    if data == "sellfiltercat":
        if not await require_seller(update):
            return True
        kb = category_keyboard("sellfiltercatpick")
        if not kb:
            await query.edit_message_text("📭 No categories found.")
            return True
        await query.edit_message_text("📂 Select a category:", reply_markup=kb)
        return True

    if data.startswith("sellfiltercatpick:"):
        if not await require_seller(update):
            return True
        cat_id_str = data.split(":", 1)[1]
        try:
            cat_id = int(cat_id_str)
        except ValueError:
            return True
        state.set(user_id, "sell_filter", f"cat:{cat_id}")
        state.set(user_id, "sell_page", 1)
        filter_str = state.get(user_id, "sell_filter")
        accounts, total = apply_list_filters(filter_str, limit=PAGE_SIZE, offset=0)
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        text = fmt_account_list_page(accounts, 1, total_pages, title="Available Accounts to Sell")
        kb = filter_page_keyboard(
            "sellfilter", 1, total_pages,
            include_available=True, include_sold=False, include_pending=False,
            include_all=False, include_ids=True,
        )
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return True

    if data == "sellfilterids":
        if not await require_seller(update):
            return True
        state.set(user_id, "sell_ids_input", True)
        await query.edit_message_text("🔢 Enter account IDs (comma-separated):")
        return True

    if data.startswith("sellfilterpage:"):
        if not await require_seller(update):
            return True
        try:
            page = int(data.split(":")[1])
        except ValueError:
            return True
        state.set(user_id, "sell_page", page)
        filter_str = state.get(user_id, "sell_filter")
        accounts, total = apply_list_filters(filter_str, limit=PAGE_SIZE, offset=(page - 1) * PAGE_SIZE)
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = max(1, min(page, total_pages))
        text = fmt_account_list_page(accounts, page, total_pages, title="Available Accounts to Sell")
        kb = filter_page_keyboard(
            "sellfilter", page, total_pages,
            include_available=True, include_sold=False, include_pending=False,
            include_all=False, include_ids=True,
        )
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return True

    if data.startswith("sellpick:"):
        if not await require_seller(update):
            return True
        try:
            account_id = int(data.split(":")[1])
        except ValueError:
            return True
        from handlers.sell import sell_select_account
        await sell_select_account(update, context, account_id)
        return True

    if data.startswith("quicksell:"):
        if not await require_seller(update):
            return True
        try:
            account_id = int(data.split(":")[1])
        except ValueError:
            return True
        from handlers.sell import sell_select_account
        state.set(user_id, "sell_filter", None)
        await sell_select_account(update, context, account_id)
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
        await query.edit_message_text(
            f"👤 Buyer: {esc(buyer_name)}\n\n💰 Enter price (₹):"
        )
        return True

    if data.startswith("paystatus:"):
        if not await require_seller(update):
            return True
        payment_status = data.split(":", 1)[1]
        state.set(user_id, "sell_payment_status", payment_status)
        account_id = state.get(user_id, "sell_account_id")
        buyer = state.get(user_id, "sell_buyer")
        price = state.get(user_id, "sell_price")
        account = get_account_by_id(account_id)
        if not account:
            await query.edit_message_text("🔍 Account not found.")
            return True
        a = _d(account)
        ps_label = "🟡 Pending Payment" if payment_status == "pending" else "🔴 Sold"
        text_preview = (
            f"<b>Confirm Sale:</b>\n\n"
            f"Account: #{a.get('id', '')} — {esc(a.get('username'))}\n"
            f"Buyer: {esc(buyer)}\n"
            f"Price: ₹{price:.0f}\n"
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
        account_id = state.pop(user_id, "sell_account_id")
        buyer = state.pop(user_id, "sell_buyer")
        price = state.pop(user_id, "sell_price", 0)
        payment_status = state.pop(user_id, "sell_payment_status", "pending")
        state.pop(user_id, "sell_stage", None)
        state.pop(user_id, "sell_filter", None)
        state.pop(user_id, "sell_page", None)
        state.pop(user_id, "sell_ids_input", None)
        for key in ("bulksell_selected", "bulksell_buyer", "bulksell_price",
                     "bulksell_payment_status", "bulksell_stage", "bulksell_filter",
                     "bulksell_page", "bulksell_count"):
            state.pop(user_id, key, None)
        if not account_id or not buyer:
            await query.edit_message_text("⚠️ Session expired. Please start over with /sell")
            return True
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
        return True

    if data == "sellcancel":
        for key in ("sell_account_id", "sell_buyer", "sell_price", "sell_payment_status",
                     "sell_stage", "sell_filter", "sell_page", "sell_ids_input"):
            state.pop(user_id, key, None)
        await query.edit_message_text("❌ Sale cancelled.")
        return True

    if data.startswith("bulksellmode:"):
        if not await require_seller(update):
            return True
        mode = data.split(":", 1)[1]
        if mode == "select":
            state.set(user_id, "bulksell_filter", "status:available")
            state.set(user_id, "bulksell_selected", [])
            state.set(user_id, "bulksell_page", 1)
            accounts, total = apply_list_filters("status:available", limit=PAGE_SIZE, offset=0)
            total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
            text = f"<b>💰 Bulk Sell — Select accounts</b>\n\n"
            for acc in accounts:
                text += fmt_account_list_line(acc) + "\n"
            kb = _bulksell_select_keyboard([], accounts, 1, total_pages)
            await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        elif mode == "number":
            state.set(user_id, "bulksell_stage", "number")
            available = count_accounts(status="available")
            await query.edit_message_text(
                f"🔢 How many accounts to sell? (available: {available})"
            )
        return True

    if data.startswith("bulkseltoggle:"):
        if not await require_seller(update):
            return True
        try:
            account_id = int(data.split(":")[1])
        except ValueError:
            return True
        selected = state.get(user_id, "bulksell_selected", [])
        if account_id in selected:
            selected.remove(account_id)
        else:
            selected.append(account_id)
        state.set(user_id, "bulksell_selected", selected)
        filter_str = state.get(user_id, "bulksell_filter")
        page = state.get(user_id, "bulksell_page", 1)
        accounts, total = apply_list_filters(filter_str, limit=PAGE_SIZE, offset=(page - 1) * PAGE_SIZE)
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        text = f"<b>💰 Bulk Sell — {len(selected)} selected</b>\n\n"
        for acc in accounts:
            text += fmt_account_list_line(acc) + "\n"
        kb = _bulksell_select_keyboard(selected, accounts, page, total_pages)
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return True

    if data.startswith("bulkselpage:"):
        if not await require_seller(update):
            return True
        try:
            page = int(data.split(":")[1])
        except ValueError:
            return True
        state.set(user_id, "bulksell_page", page)
        filter_str = state.get(user_id, "bulksell_filter")
        selected = state.get(user_id, "bulksell_selected", [])
        accounts, total = apply_list_filters(filter_str, limit=PAGE_SIZE, offset=(page - 1) * PAGE_SIZE)
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        text = f"<b>💰 Bulk Sell — {len(selected)} selected</b>\n\n"
        for acc in accounts:
            text += fmt_account_list_line(acc) + "\n"
        kb = _bulksell_select_keyboard(selected, accounts, page, total_pages)
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return True

    if data == "bulkselldone":
        if not await require_seller(update):
            return True
        selected = state.get(user_id, "bulksell_selected", [])
        if not selected:
            await query.edit_message_text("⚠️ No accounts selected.")
            return True
        state.set(user_id, "bulksell_stage", "buyer")
        buyer_names = get_buyer_names()
        if buyer_names:
            kb = buyer_keyboard(buyer_names, "bulkbuypick")
            await query.edit_message_text(
                f"👤 {len(selected)} accounts selected.\nSelect buyer:",
                reply_markup=kb,
            )
        else:
            await query.edit_message_text(f"👤 {len(selected)} accounts selected.\nEnter buyer name:")
        return True

    if data.startswith("bulkbuypick:"):
        if not await require_seller(update):
            return True
        buyer_name = data.split(":", 1)[1]
        if buyer_name == "new":
            state.set(user_id, "bulksell_stage", "buyer")
            await query.edit_message_text("👤 Enter buyer name:")
            return True
        state.set(user_id, "bulksell_buyer", buyer_name)
        state.set(user_id, "bulksell_stage", "price")
        await query.edit_message_text(f"👤 Buyer: {esc(buyer_name)}\n\n💰 Enter price per account (₹):")
        return True

    if data.startswith("bulksellpaystatus:"):
        if not await require_seller(update):
            return True
        payment_status = data.split(":", 1)[1]
        state.set(user_id, "bulksell_payment_status", payment_status)
        seller = get_seller_by_user_id(user_id)
        if not seller:
            await query.edit_message_text("⚠️ You are not registered as a seller.")
            return True
        selected = state.pop(user_id, "bulksell_selected", [])
        buyer = state.pop(user_id, "bulksell_buyer")
        price = state.pop(user_id, "bulksell_price", 0)
        state.pop(user_id, "bulksell_stage", None)
        state.pop(user_id, "bulksell_filter", None)
        state.pop(user_id, "bulksell_page", None)
        for key in ("sell_account_id", "sell_buyer", "sell_price", "sell_payment_status",
                     "sell_stage", "sell_filter", "sell_page", "sell_ids_input"):
            state.pop(user_id, key, None)
        if not selected or not buyer:
            await query.edit_message_text("❌ Bulk sell cancelled — no accounts selected.")
            return True
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

    if data == "bulksellcancel":
        for key in ("bulksell_selected", "bulksell_buyer", "bulksell_price",
                     "bulksell_payment_status", "bulksell_stage", "bulksell_filter", "bulksell_page"):
            state.pop(user_id, key, None)
        await query.edit_message_text("❌ Bulk sell cancelled.")
        return True

    return False
