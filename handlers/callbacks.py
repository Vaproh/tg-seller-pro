import logging
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.permissions import require_seller, require_admin, get_user_role
from core.state import state
from core.format import esc, _d, fmt_account_block, fmt_receipt, fmt_sale_block
from core.keyboards import (
    main_menu_keyboard, add_menu_keyboard, settings_keyboard,
    confirm_keyboard, category_keyboard, yes_no_keyboard,
    report_period_keyboard, sale_actions_keyboard,
)
from core.filters import (
    filter_page_keyboard, apply_list_filters, count_from_filter,
    fmt_account_list_page, parse_filter_state, build_filter_state,
    parse_id_list, buyer_keyboard, payment_status_keyboard,
    fmt_account_list_line, category_keyboard_with_all, PAGE_SIZE,
)
from database import (
    list_categories, get_category_name, delete_account, delete_category,
    list_accounts, count_accounts, get_account_by_id, get_category_id_by_name,
    sell_account, mark_payment, void_sale, get_sale_by_id, get_sales, count_sales,
    add_accounts_bulk, export_accounts_csv, set_account_status,
    get_buyer_names, get_buyer_sales, get_seller_by_user_id,
    get_available_accounts_for_category,
)
from database.sales import bulk_sell_accounts, get_sales_summary
from utils.csv_utils import build_accounts_from_csv
from handlers.preview import handle_preview_category
from handlers.search import (
    handle_search_type, handle_search_value,
    handle_search_category, handle_search_status,
)
from handlers.reports import handle_report_period
from utils.notifications import (
    notify_admin, fmt_payment_notification, fmt_void_notification,
)
import config

logger = logging.getLogger(__name__)

MAX_MSG_LEN = 4000


def _truncate(text, limit=MAX_MSG_LEN):
    if len(text) <= limit:
        return text
    return text[:limit - 20] + "\n\n... (truncated)"


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    await query.answer()

    if data == "noop":
        return

    # ── Main menu ──────────────────────────────────────────
    if data == "menu:back":
        role = get_user_role(user_id)
        is_admin = role == "admin"
        kb = main_menu_keyboard(is_admin=is_admin)
        await query.edit_message_text("📋 Main Menu", reply_markup=kb)
        return

    # ── Add account menu ───────────────────────────────────
    if data == "menu:add":
        if not await require_admin(update):
            return
        await query.edit_message_text("➕ Add account:", reply_markup=add_menu_keyboard())
        return

    if data == "menu:add:single":
        if not await require_admin(update):
            return
        state.set(user_id, "add_stage", "username")
        await query.edit_message_text("👤 Send the Reddit username:")
        return

    if data == "menu:add:bulk":
        if not await require_admin(update):
            return
        kb = category_keyboard("bulkcat")
        if not kb:
            await query.edit_message_text("📂 No categories. Create one first with /addcategory")
            return
        state.set(user_id, "bulk_stage", "category")
        await query.edit_message_text("📂 Select a category for bulk import:", reply_markup=kb)
        return

    if data == "menu:add:csv":
        if not await require_admin(update):
            return
        kb = category_keyboard("csvcat")
        if not kb:
            await query.edit_message_text("📂 No categories. Create one first with /addcategory")
            return
        state.set(user_id, "csv_stage", "category")
        await query.edit_message_text("📂 Select a category for CSV import:", reply_markup=kb)
        return

    # ── Add wizard callbacks ───────────────────────────────
    if data.startswith("add2fa:"):
        if not await require_admin(update):
            return
        val = data.split(":")[1] == "yes"
        state.set(user_id, "add_2fa", val)
        state.set(user_id, "add_stage", "verified")
        label = "Yes" if val else "No"
        await query.edit_message_text(
            f"✅ 2FA: {label}\nIs the account verified?",
            reply_markup=yes_no_keyboard("addverified"),
        )
        return

    if data.startswith("addverified:"):
        if not await require_admin(update):
            return
        val = data.split(":")[1] == "yes"
        state.set(user_id, "add_verified", val)
        state.set(user_id, "add_stage", "notes")
        label = "Yes" if val else "No"
        await query.edit_message_text(
            f"✅ Verified: {label}\nAny notes? (or /skip)"
        )
        return

    if data.startswith("addcat:"):
        if not await require_admin(update):
            return
        cat_id_str = data.split(":", 1)[1]
        try:
            cat_id = int(cat_id_str)
        except ValueError:
            return
        state.set(user_id, "add_category_id", cat_id)
        state.set(user_id, "add_stage", "confirm")
        username = state.get(user_id, "add_username", "—")
        password = state.get(user_id, "add_password", "—")
        email = state.get(user_id, "add_email")
        email_password = state.get(user_id, "add_email_password")
        has_2fa = state.get(user_id, "add_2fa", False)
        is_verified = state.get(user_id, "add_verified", False)
        notes = state.get(user_id, "add_notes")
        cat_name = get_category_name(cat_id) or "—"
        preview = (
            f"<b>Confirm account:</b>\n\n"
            f"👤 Username: {esc(username)}\n"
            f"🔑 Password: <tg-spoiler>{esc(password)}</tg-spoiler>\n"
        )
        if email:
            preview += f"📧 Email: {esc(email)}\n"
        if email_password:
            preview += f"🔑 Email Pass: <tg-spoiler>{esc(email_password)}</tg-spoiler>\n"
        preview += f"🔐 2FA: {'Yes' if has_2fa else 'No'}\n"
        preview += f"✅ Verified: {'Yes' if is_verified else 'No'}\n"
        if notes:
            preview += f"📝 Notes: {esc(notes)}\n"
        preview += f"📂 Category: {esc(cat_name)}\n\nConfirm?"
        await query.edit_message_text(
            preview,
            parse_mode="HTML",
            reply_markup=confirm_keyboard("addconfirm", "addcancel"),
        )
        return

    if data == "addconfirm":
        if not await require_admin(update):
            return
        username = state.pop(user_id, "add_username")
        password = state.pop(user_id, "add_password")
        email = state.pop(user_id, "add_email")
        email_password = state.pop(user_id, "add_email_password")
        has_2fa = state.pop(user_id, "add_2fa", False)
        is_verified = state.pop(user_id, "add_verified", False)
        notes = state.pop(user_id, "add_notes")
        cat_id = state.pop(user_id, "add_category_id")
        state.pop(user_id, "add_stage")
        if not username or not password:
            await query.edit_message_text("❌ Add cancelled — missing data.")
            return
        success, msg, acc_id = add_account(
            username, password, cat_id,
            email=email, email_password=email_password,
            has_2fa=has_2fa, is_verified=is_verified, notes=notes,
        )
        if success:
            await query.edit_message_text(f"✅ Account saved! (ID: #{acc_id})")
        else:
            await query.edit_message_text(f"❌ {msg}")
        return

    if data == "addcancel":
        if not await require_admin(update):
            return
        for key in ("add_username", "add_password", "add_email", "add_email_password",
                     "add_2fa", "add_verified", "add_notes", "add_category_id", "add_stage"):
            state.pop(user_id, key, None)
        await query.edit_message_text("❌ Account add cancelled.")
        return

    # ── Preview ────────────────────────────────────────────
    if data == "menu:preview":
        kb = category_keyboard("previewcat", include_all=True)
        if not kb:
            await query.edit_message_text("📭 No categories found.")
            return
        await query.edit_message_text("📂 Select a category:", reply_markup=kb)
        return

    if data.startswith("previewcat:"):
        cat_id_str = data.split(":", 1)[1]
        await handle_preview_category(update, context, cat_id_str)
        return

    # ── Sell flow ──────────────────────────────────────────
    if data == "menu:sell":
        if not await require_seller(update):
            return
        seller = get_seller_by_user_id(user_id)
        if not seller:
            await query.edit_message_text("⚠️ You are not registered as a seller.")
            return
        state.set(user_id, "sell_filter", None)
        state.set(user_id, "sell_page", 1)
        accounts, total = apply_list_filters(None, limit=PAGE_SIZE, offset=0)
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        text = fmt_account_list_page(accounts, 1, total_pages, title="Available Accounts to Sell")
        kb = filter_page_keyboard(
            "sellfilter", 1, total_pages,
            include_available=True, include_sold=False, include_pending=False,
            include_all=False, include_ids=True,
        )
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return

    # ── Sell filter callbacks ──────────────────────────────
    if data.startswith("sellfilter:") and not data.startswith("sellfiltercat") and not data.startswith("sellfilterids"):
        if not await require_seller(update):
            return
        f = data.split(":", 1)[1]
        if f == "all":
            state.set(user_id, "sell_filter", None)
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
        return

    if data == "sellfiltercat":
        if not await require_seller(update):
            return
        kb = category_keyboard("sellfiltercatpick")
        if not kb:
            await query.edit_message_text("📭 No categories found.")
            return
        await query.edit_message_text("📂 Select a category:", reply_markup=kb)
        return

    if data.startswith("sellfiltercatpick:"):
        if not await require_seller(update):
            return
        cat_id_str = data.split(":", 1)[1]
        try:
            cat_id = int(cat_id_str)
        except ValueError:
            return
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
        return

    if data == "sellfilterids":
        if not await require_seller(update):
            return
        state.set(user_id, "sell_ids_input", True)
        await query.edit_message_text("🔢 Enter account IDs (comma-separated):")
        return

    if data.startswith("sellfilterpage:"):
        if not await require_seller(update):
            return
        try:
            page = int(data.split(":")[1])
        except ValueError:
            return
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
        return

    # ── Sell account selection ─────────────────────────────
    if data.startswith("sellpick:"):
        if not await require_seller(update):
            return
        try:
            account_id = int(data.split(":")[1])
        except ValueError:
            return
        from handlers.sell import sell_select_account
        await sell_select_account(update, context, account_id)
        return

    if data.startswith("quicksell:"):
        if not await require_seller(update):
            return
        try:
            account_id = int(data.split(":")[1])
        except ValueError:
            return
        from handlers.sell import sell_select_account
        state.set(user_id, "sell_filter", None)
        await sell_select_account(update, context, account_id)
        return

    # ── Buyer selection ────────────────────────────────────
    if data.startswith("buypick:"):
        if not await require_seller(update):
            return
        buyer_name = data.split(":", 1)[1]
        if buyer_name == "new":
            state.set(user_id, "sell_stage", "buyer")
            await query.edit_message_text("👤 Enter buyer name:")
            return
        state.set(user_id, "sell_buyer", buyer_name)
        state.set(user_id, "sell_stage", "price")
        await query.edit_message_text(
            f"👤 Buyer: {esc(buyer_name)}\n\n💰 Enter price (₹):"
        )
        return

    # ── Payment status choice ──────────────────────────────
    if data.startswith("paystatus:"):
        if not await require_seller(update):
            return
        payment_status = data.split(":", 1)[1]
        state.set(user_id, "sell_payment_status", payment_status)
        account_id = state.get(user_id, "sell_account_id")
        buyer = state.get(user_id, "sell_buyer")
        price = state.get(user_id, "sell_price")
        account = get_account_by_id(account_id)
        if not account:
            await query.edit_message_text("🔍 Account not found.")
            return
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
        return

    if data == "sellconfirm":
        if not await require_seller(update):
            return
        seller = get_seller_by_user_id(user_id)
        if not seller:
            await query.edit_message_text("⚠️ You are not registered as a seller.")
            return
        account_id = state.pop(user_id, "sell_account_id")
        buyer = state.pop(user_id, "sell_buyer")
        price = state.pop(user_id, "sell_price", 0)
        payment_status = state.pop(user_id, "sell_payment_status", "pending")
        state.pop(user_id, "sell_stage", None)
        state.pop(user_id, "sell_filter", None)
        state.pop(user_id, "sell_page", None)
        state.pop(user_id, "sell_ids_input", None)
        if not account_id or not buyer:
            await query.edit_message_text("❌ Sell cancelled — missing data.")
            return
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
        return

    if data == "sellcancel":
        for key in ("sell_account_id", "sell_buyer", "sell_price", "sell_payment_status",
                     "sell_stage", "sell_filter", "sell_page", "sell_ids_input"):
            state.pop(user_id, key, None)
        await query.edit_message_text("❌ Sale cancelled.")
        return

    # ── Bulk sell ──────────────────────────────────────────
    if data.startswith("bulksellmode:"):
        if not await require_seller(update):
            return
        mode = data.split(":", 1)[1]
        if mode == "select":
            state.set(user_id, "bulksell_filter", None)
            state.set(user_id, "bulksell_selected", [])
            state.set(user_id, "bulksell_page", 1)
            accounts, total = apply_list_filters(None, limit=PAGE_SIZE, offset=0)
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
        return

    if data.startswith("bulkseltoggle:"):
        if not await require_seller(update):
            return
        try:
            account_id = int(data.split(":")[1])
        except ValueError:
            return
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
        return

    if data.startswith("bulkselpage:"):
        if not await require_seller(update):
            return
        try:
            page = int(data.split(":")[1])
        except ValueError:
            return
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
        return

    if data == "bulkselldone":
        if not await require_seller(update):
            return
        selected = state.get(user_id, "bulksell_selected", [])
        if not selected:
            await query.edit_message_text("⚠️ No accounts selected.")
            return
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
        return

    if data.startswith("bulkbuypick:"):
        if not await require_seller(update):
            return
        buyer_name = data.split(":", 1)[1]
        if buyer_name == "new":
            state.set(user_id, "bulksell_stage", "buyer")
            await query.edit_message_text("👤 Enter buyer name:")
            return
        state.set(user_id, "bulksell_buyer", buyer_name)
        state.set(user_id, "bulksell_stage", "price")
        await query.edit_message_text(f"👤 Buyer: {esc(buyer_name)}\n\n💰 Enter price per account (₹):")
        return

    if data.startswith("bulksellpaystatus:"):
        if not await require_seller(update):
            return
        payment_status = data.split(":", 1)[1]
        state.set(user_id, "bulksell_payment_status", payment_status)
        seller = get_seller_by_user_id(user_id)
        if not seller:
            await query.edit_message_text("⚠️ You are not registered as a seller.")
            return
        selected = state.pop(user_id, "bulksell_selected", [])
        buyer = state.pop(user_id, "bulksell_buyer")
        price = state.pop(user_id, "bulksell_price", 0)
        state.pop(user_id, "bulksell_stage", None)
        state.pop(user_id, "bulksell_filter", None)
        state.pop(user_id, "bulksell_page", None)
        if not selected or not buyer:
            await query.edit_message_text("❌ Bulk sell cancelled — no accounts selected.")
            return
        result = bulk_sell_accounts(
            selected, seller["id"], buyer, price,
            payment_status=payment_status,
        )
        status_label = "pending payment" if payment_status == "pending" else "sold"
        await query.edit_message_text(
            f"✅ Bulk sell complete: {result['added']} {status_label}, {result['skipped']} skipped"
        )
        await notify_admin(context, f"💰 Bulk sell: {result['added']} accounts to {buyer} — ₹{price:.0f} each ({status_label}) — by {seller['name']}")
        return

    if data == "bulksellcancel":
        for key in ("bulksell_selected", "bulksell_buyer", "bulksell_price",
                     "bulksell_payment_status", "bulksell_stage", "bulksell_filter", "bulksell_page"):
            state.pop(user_id, key, None)
        await query.edit_message_text("❌ Bulk sell cancelled.")
        return

    # ── Sales ──────────────────────────────────────────────
    if data == "menu:sales":
        if not await require_seller(update):
            return
        role = get_user_role(user_id)
        seller = get_seller_by_user_id(user_id) if role != "admin" else None
        seller_id = seller["id"] if seller else None
        state.set(user_id, "sales_page", 1)
        state.set(user_id, "sales_filter", None)
        total = count_sales(seller_id=seller_id)
        if total == 0:
            await query.edit_message_text("📭 No sales found.")
            return
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        sales = get_sales(limit=PAGE_SIZE, offset=0, seller_id=seller_id)
        from handlers.sell import _fmt_sales_page, _sales_keyboard
        text = _fmt_sales_page(sales, 1, total_pages)
        kb = _sales_keyboard(1, total_pages)
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return

    if data.startswith("salesfilter:") and not data.startswith("salesfilterpage:"):
        if not await require_seller(update):
            return
        f = data.split(":", 1)[1]
        state.set(user_id, "sales_filter", f)
        state.set(user_id, "sales_page", 1)
        role = get_user_role(user_id)
        seller = get_seller_by_user_id(user_id) if role != "admin" else None
        seller_id = seller["id"] if seller else None
        status_val = f if f != "all" else None
        total = count_sales(seller_id=seller_id, status=status_val)
        if total == 0:
            await query.edit_message_text("📭 No sales found.")
            return
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        sales = get_sales(limit=PAGE_SIZE, offset=0, seller_id=seller_id, status=status_val)
        from handlers.sell import _fmt_sales_page, _sales_keyboard
        text = _fmt_sales_page(sales, 1, total_pages)
        kb = _sales_keyboard(1, total_pages)
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return

    if data.startswith("salesfilterpage:"):
        if not await require_seller(update):
            return
        try:
            page = int(data.split(":")[1])
        except ValueError:
            return
        role = get_user_role(user_id)
        seller = get_seller_by_user_id(user_id) if role != "admin" else None
        seller_id = seller["id"] if seller else None
        sf = state.get(user_id, "sales_filter")
        status_val = sf if sf and sf != "all" else None
        total = count_sales(seller_id=seller_id, status=status_val)
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = max(1, min(page, total_pages))
        state.set(user_id, "sales_page", page)
        sales = get_sales(limit=PAGE_SIZE, offset=(page - 1) * PAGE_SIZE, seller_id=seller_id, status=status_val)
        from handlers.sell import _fmt_sales_page, _sales_keyboard
        text = _fmt_sales_page(sales, page, total_pages)
        kb = _sales_keyboard(page, total_pages)
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return

    # ── List accounts ──────────────────────────────────────
    if data == "menu:list":
        if not await require_seller(update):
            return
        state.set(user_id, "list_filter", None)
        state.set(user_id, "list_page", 1)
        accounts, total = apply_list_filters(None, limit=PAGE_SIZE, offset=0)
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        text = fmt_account_list_page(accounts, 1, total_pages, title="Accounts")
        kb = filter_page_keyboard(
            "listfilter", 1, total_pages,
            include_all=True, include_available=True, include_sold=True,
            include_pending=True, include_ids=True,
        )
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return

    if data.startswith("listfilter:") and not data.startswith("listfiltercat") and not data.startswith("listfilterids") and not data.startswith("listfilterpage:"):
        if not await require_seller(update):
            return
        f = data.split(":", 1)[1]
        if f == "all":
            state.set(user_id, "list_filter", None)
        else:
            state.set(user_id, "list_filter", f"status:{f}")
        state.set(user_id, "list_page", 1)
        filter_str = state.get(user_id, "list_filter")
        accounts, total = apply_list_filters(filter_str, limit=PAGE_SIZE, offset=0)
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        text = fmt_account_list_page(accounts, 1, total_pages, title="Accounts")
        kb = filter_page_keyboard(
            "listfilter", 1, total_pages,
            include_all=True, include_available=True, include_sold=True,
            include_pending=True, include_ids=True,
        )
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return

    if data == "listfiltercat":
        if not await require_seller(update):
            return
        kb = category_keyboard("listfiltercatpick")
        if not kb:
            await query.edit_message_text("📭 No categories found.")
            return
        await query.edit_message_text("📂 Select a category:", reply_markup=kb)
        return

    if data.startswith("listfiltercatpick:"):
        if not await require_seller(update):
            return
        cat_id_str = data.split(":", 1)[1]
        try:
            cat_id = int(cat_id_str)
        except ValueError:
            return
        state.set(user_id, "list_filter", f"cat:{cat_id}")
        state.set(user_id, "list_page", 1)
        filter_str = state.get(user_id, "list_filter")
        accounts, total = apply_list_filters(filter_str, limit=PAGE_SIZE, offset=0)
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        text = fmt_account_list_page(accounts, 1, total_pages, title="Accounts")
        kb = filter_page_keyboard(
            "listfilter", 1, total_pages,
            include_all=True, include_available=True, include_sold=True,
            include_pending=True, include_ids=True,
        )
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return

    if data == "listfilterids":
        if not await require_seller(update):
            return
        state.set(user_id, "list_ids_input", True)
        await query.edit_message_text("🔢 Enter account IDs (comma-separated):")
        return

    if data.startswith("listfilterpage:"):
        if not await require_seller(update):
            return
        try:
            page = int(data.split(":")[1])
        except ValueError:
            return
        state.set(user_id, "list_page", page)
        filter_str = state.get(user_id, "list_filter")
        accounts, total = apply_list_filters(filter_str, limit=PAGE_SIZE, offset=(page - 1) * PAGE_SIZE)
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = max(1, min(page, total_pages))
        text = fmt_account_list_page(accounts, page, total_pages, title="Accounts")
        kb = filter_page_keyboard(
            "listfilter", page, total_pages,
            include_all=True, include_available=True, include_sold=True,
            include_pending=True, include_ids=True,
        )
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return

    # ── Delete flow ────────────────────────────────────────
    if data.startswith("delfilter:") and not data.startswith("delfiltercat") and not data.startswith("delfilterids") and not data.startswith("delfilterpage:"):
        if not await require_admin(update):
            return
        f = data.split(":", 1)[1]
        if f == "all":
            state.set(user_id, "delete_filter", None)
        else:
            state.set(user_id, "delete_filter", f"status:{f}")
        state.set(user_id, "delete_page", 1)
        filter_str = state.get(user_id, "delete_filter")
        accounts, total = apply_list_filters(filter_str, limit=PAGE_SIZE, offset=0)
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        text = fmt_account_list_page(accounts, 1, total_pages, title="Delete Accounts")
        kb = filter_page_keyboard(
            "delfilter", 1, total_pages,
            include_all=True, include_available=True, include_sold=True,
            include_pending=True, include_ids=True,
        )
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return

    if data == "delfiltercat":
        if not await require_admin(update):
            return
        kb = category_keyboard("delfiltercatpick")
        if not kb:
            await query.edit_message_text("📭 No categories found.")
            return
        await query.edit_message_text("📂 Select a category:", reply_markup=kb)
        return

    if data.startswith("delfiltercatpick:"):
        if not await require_admin(update):
            return
        cat_id_str = data.split(":", 1)[1]
        try:
            cat_id = int(cat_id_str)
        except ValueError:
            return
        state.set(user_id, "delete_filter", f"cat:{cat_id}")
        state.set(user_id, "delete_page", 1)
        filter_str = state.get(user_id, "delete_filter")
        accounts, total = apply_list_filters(filter_str, limit=PAGE_SIZE, offset=0)
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        text = fmt_account_list_page(accounts, 1, total_pages, title="Delete Accounts")
        kb = filter_page_keyboard(
            "delfilter", 1, total_pages,
            include_all=True, include_available=True, include_sold=True,
            include_pending=True, include_ids=True,
        )
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return

    if data == "delfilterids":
        if not await require_admin(update):
            return
        state.set(user_id, "del_ids_input", True)
        await query.edit_message_text("🔢 Enter account IDs to delete (comma-separated):")
        return

    if data.startswith("delfilterpage:"):
        if not await require_admin(update):
            return
        try:
            page = int(data.split(":")[1])
        except ValueError:
            return
        state.set(user_id, "delete_page", page)
        filter_str = state.get(user_id, "delete_filter")
        accounts, total = apply_list_filters(filter_str, limit=PAGE_SIZE, offset=(page - 1) * PAGE_SIZE)
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = max(1, min(page, total_pages))
        text = fmt_account_list_page(accounts, page, total_pages, title="Delete Accounts")
        kb = filter_page_keyboard(
            "delfilter", page, total_pages,
            include_all=True, include_available=True, include_sold=True,
            include_pending=True, include_ids=True,
        )
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return

    if data.startswith("delsingle:"):
        if not await require_admin(update):
            return
        try:
            account_id = int(data.split(":")[1])
        except ValueError:
            return
        account = get_account_by_id(account_id)
        if not account:
            await query.edit_message_text("🔍 Account not found.")
            return
        state.set(user_id, "delete_confirm", account_id)
        await query.edit_message_text(
            f"⚠️ Delete account #{account_id} ({esc(_d(account)['username'])})?",
            reply_markup=confirm_keyboard(f"delconfirm:{account_id}", "delcancel"),
        )
        return

    if data.startswith("delconfirm:"):
        if not await require_admin(update):
            return
        parts = data.split(":")
        try:
            account_id = int(parts[1])
        except ValueError:
            return
        state.pop(user_id, "delete_confirm", None)
        success = delete_account(account_id)
        if success:
            await query.edit_message_text(f"✅ Account #{account_id} deleted.")
        else:
            await query.edit_message_text("❌ Failed to delete account.")
        return

    if data == "delcancel":
        state.pop(user_id, "delete_confirm", None)
        await query.edit_message_text("❌ Deletion cancelled.")
        return

    # ── Inventory ──────────────────────────────────────────
    if data == "menu:inventory":
        if not await require_seller(update):
            return
        from handlers.inventory import inventory_cmd
        state.set(user_id, "inv_filter", None)
        state.set(user_id, "inv_page", 1)
        cats = list_categories()
        if not cats:
            await query.edit_message_text("📭 No categories found.")
            return
        available = count_accounts(status="available")
        sold = count_accounts(status="sold")
        pending = count_accounts(status="pending_payment")
        summary = get_sales_summary()
        text = "<b>📦 Inventory Overview</b>\n\n"
        text += f"🟢 Available: {available}\n"
        text += f"🔴 Sold: {sold}\n"
        text += f"🟡 Pending Payment: {pending}\n"
        text += f"💰 Total revenue: ₹{summary.get('total_revenue', 0):.0f}\n"
        text += f"💳 Pending: ₹{summary.get('pending_amount', 0):.0f}\n\n"
        text += "<b>📂 By Category:</b>\n"
        for cat in cats:
            cat_avail = count_accounts(category_id=cat["id"], status="available")
            cat_sold = count_accounts(category_id=cat["id"], status="sold")
            cat_pend = count_accounts(category_id=cat["id"], status="pending_payment")
            text += f"• {esc(cat['name'])}: 🟢{cat_avail} 🔴{cat_sold} 🟡{cat_pend}\n"
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🟢 Available", callback_data="invfilter:available"),
                InlineKeyboardButton("🔴 Sold", callback_data="invfilter:sold"),
            ],
            [
                InlineKeyboardButton("🟡 Pending", callback_data="invfilter:pending_payment"),
                InlineKeyboardButton("📋 All", callback_data="invfilter:all"),
            ],
            [
                InlineKeyboardButton("📂 By Category", callback_data="invfiltercat"),
            ],
        ])
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return

    if data.startswith("invfilter:") and not data.startswith("invfiltercat") and not data.startswith("invfilterpage:"):
        if not await require_seller(update):
            return
        f = data.split(":", 1)[1]
        if f == "all":
            state.set(user_id, "inv_filter", None)
        else:
            state.set(user_id, "inv_filter", f"status:{f}")
        state.set(user_id, "inv_page", 1)
        filter_str = state.get(user_id, "inv_filter")
        accounts, total = apply_list_filters(filter_str, limit=PAGE_SIZE, offset=0)
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        text = fmt_account_list_page(accounts, 1, total_pages, title="Inventory")
        kb = filter_page_keyboard(
            "invfilter", 1, total_pages,
            include_all=True, include_available=True, include_sold=True,
            include_pending=True,
        )
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return

    if data == "invfiltercat":
        if not await require_seller(update):
            return
        kb = category_keyboard("invfiltercatpick")
        if not kb:
            await query.edit_message_text("📭 No categories found.")
            return
        await query.edit_message_text("📂 Select a category:", reply_markup=kb)
        return

    if data.startswith("invfiltercatpick:"):
        if not await require_seller(update):
            return
        cat_id_str = data.split(":", 1)[1]
        try:
            cat_id = int(cat_id_str)
        except ValueError:
            return
        state.set(user_id, "inv_filter", f"cat:{cat_id}")
        state.set(user_id, "inv_page", 1)
        filter_str = state.get(user_id, "inv_filter")
        accounts, total = apply_list_filters(filter_str, limit=PAGE_SIZE, offset=0)
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        text = fmt_account_list_page(accounts, 1, total_pages, title="Inventory")
        kb = filter_page_keyboard(
            "invfilter", 1, total_pages,
            include_all=True, include_available=True, include_sold=True,
            include_pending=True,
        )
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return

    if data.startswith("invfilterpage:"):
        if not await require_seller(update):
            return
        try:
            page = int(data.split(":")[1])
        except ValueError:
            return
        state.set(user_id, "inv_page", page)
        filter_str = state.get(user_id, "inv_filter")
        accounts, total = apply_list_filters(filter_str, limit=PAGE_SIZE, offset=(page - 1) * PAGE_SIZE)
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = max(1, min(page, total_pages))
        text = fmt_account_list_page(accounts, page, total_pages, title="Inventory")
        kb = filter_page_keyboard(
            "invfilter", page, total_pages,
            include_all=True, include_available=True, include_sold=True,
            include_pending=True,
        )
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return

    # ── Mark account status ────────────────────────────────
    if data.startswith("markstatus:"):
        if not await require_seller(update):
            return
        parts = data.split(":", 2)
        try:
            account_id = int(parts[1])
            new_status = parts[2]
        except (ValueError, IndexError):
            return
        if new_status not in ("available", "sold", "pending_payment"):
            return
        success = set_account_status(account_id, new_status)
        if success:
            emoji = {"available": "🟢", "sold": "🔴", "pending_payment": "🟡"}.get(new_status, "⚪")
            await query.edit_message_text(f"✅ Account #{account_id} marked as {emoji} {new_status}.")
        else:
            await query.edit_message_text("❌ Failed to update status.")
        return

    # ── Mark sale status (from /sale view) ─────────────────
    if data.startswith("markpaid:"):
        if not await require_seller(update):
            return
        try:
            sale_id = int(data.split(":")[1])
        except ValueError:
            return
        sale = get_sale_by_id(sale_id)
        if not sale:
            await query.edit_message_text("🔍 Sale not found.")
            return
        role = get_user_role(user_id)
        if role != "admin" and _d(sale).get("seller_user_id") != user_id:
            await query.edit_message_text("⚠️ You can only mark your own sales as paid.")
            return
        new_status = "paid" if _d(sale).get("payment_status") == "pending" else "pending"
        mark_payment(sale_id, new_status)
        label = "paid" if new_status == "paid" else "pending"
        await query.edit_message_text(f"✅ Sale #{sale_id} marked as {label}.")
        if new_status == "paid":
            await notify_admin(context, f"✅ Payment received! Sale #{sale_id} — ₹{_d(sale).get('price', 0):.0f} from {_d(sale).get('buyer_name')}")
        return

    if data.startswith("marksaleunsold:"):
        if not await require_seller(update):
            return
        try:
            sale_id = int(data.split(":")[1])
        except ValueError:
            return
        sale = get_sale_by_id(sale_id)
        if not sale:
            await query.edit_message_text("🔍 Sale not found.")
            return
        sd = _d(sale)
        void_sale(sale_id)
        await query.edit_message_text(f"✅ Sale #{sale_id} voided. Account returned to available stock.")
        await notify_admin(context, fmt_void_notification(sale_id))
        return

    if data.startswith("marksalepending:"):
        if not await require_seller(update):
            return
        try:
            sale_id = int(data.split(":")[1])
        except ValueError:
            return
        sale = get_sale_by_id(sale_id)
        if not sale:
            await query.edit_message_text("🔍 Sale not found.")
            return
        mark_payment(sale_id, "pending")
        await query.edit_message_text(f"✅ Sale #{sale_id} marked as 🟡 pending payment.")
        return

    # ── Void sale confirm/cancel ───────────────────────────
    if data.startswith("voidconfirm:"):
        if not await require_admin(update):
            return
        try:
            sale_id = int(data.split(":")[1])
        except ValueError:
            return
        state.pop(user_id, "void_confirm", None)
        success = void_sale(sale_id)
        if success:
            await query.edit_message_text(f"✅ Sale #{sale_id} voided. Account returned to available stock.")
            await notify_admin(context, fmt_void_notification(sale_id))
        else:
            await query.edit_message_text("❌ Failed to void sale.")
        return

    if data == "voidcancel":
        state.pop(user_id, "void_confirm", None)
        await query.edit_message_text("❌ Void cancelled.")
        return

    # ── Stats ──────────────────────────────────────────────
    if data == "menu:stats":
        from database.sessions import stats_summary
        stats = stats_summary()
        text = (
            f"<b>📊 Statistics</b>\n\n"
            f"📦 Total accounts: {stats['total_accounts']}\n"
            f"✅ Used: {stats['used_accounts']}\n"
            f"📋 Sessions: {stats['total_sessions']}\n\n"
            f"<b>By Category:</b>\n"
        )
        for c in stats["categories"]:
            text += f"• {esc(c['name'])}: {c['count']}\n"
        await query.edit_message_text(text, parse_mode="HTML")
        return

    # ── Sellers ────────────────────────────────────────────
    if data == "menu:sellers":
        if not await require_admin(update):
            return
        from database import list_sellers
        sellers = list_sellers()
        if not sellers:
            await query.edit_message_text("📭 No sellers registered.")
            return
        text = "<b>👥 Sellers</b>\n\n"
        for s in sellers:
            status = "🟢" if s["active"] else "🔴"
            text += (
                f"{status} {esc(s['name'])} (ID: {s['user_id']}) — "
                f"{s['sale_count']} sales, ₹{s['total_earnings']:.0f}\n"
            )
        await query.edit_message_text(text, parse_mode="HTML")
        return

    # ── Report ─────────────────────────────────────────────
    if data == "menu:report":
        if not await require_admin(update):
            return
        await query.edit_message_text("📊 Select a period:", reply_markup=report_period_keyboard())
        return

    if data.startswith("report:"):
        if not await require_admin(update):
            return
        period = data.split(":", 1)[1]
        await handle_report_period(update, context, period)
        return

    # ── Settings ───────────────────────────────────────────
    if data == "menu:settings":
        if not await require_admin(update):
            return
        await query.edit_message_text("⚙️ Settings:", reply_markup=settings_keyboard())
        return

    # ── Export (safe for callback context) ─────────────────
    if data == "menu:export":
        if not await require_admin(update):
            return
        csv_data = export_accounts_csv()
        filename = f"accounts_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join("/tmp", filename)
        try:
            with open(filepath, "wb") as f:
                f.write(csv_data)
            with open(filepath, "rb") as f:
                await context.bot.send_document(
                    chat_id=user_id,
                    document=f,
                    filename=filename,
                    caption="📤 Accounts export",
                )
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)
        return

    if data == "menu:backup":
        if not await require_admin(update):
            return
        from database.connection import DB_PATH
        if not os.path.exists(DB_PATH):
            await context.bot.send_message(chat_id=user_id, text="📭 No database found.")
            return
        filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        filepath = os.path.join("/tmp", filename)
        try:
            import shutil
            shutil.copy2(DB_PATH, filepath)
            with open(filepath, "rb") as f:
                await context.bot.send_document(
                    chat_id=user_id,
                    document=f,
                    filename=filename,
                    caption="💾 Database backup",
                )
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)
        return

    # ── Bulk add category selection ────────────────────────
    if data.startswith("bulkcat:"):
        cat_id_str = data.split(":", 1)[1]
        if cat_id_str == "all":
            return
        try:
            cat_id = int(cat_id_str)
        except ValueError:
            return
        cat_name = get_category_name(cat_id)
        if not cat_name:
            await query.edit_message_text("🔍 Category not found.")
            return
        state.set(user_id, "bulk_category", cat_id)
        state.set(user_id, "bulk_stage", "lines")
        await query.edit_message_text(
            f"Category: {cat_name}\n\n"
            "Send accounts in format:\n<code>user:pass</code>\n"
            "One per line. Send /done when finished.",
            parse_mode="HTML",
        )
        return

    # ── CSV category selection ─────────────────────────────
    if data.startswith("csvcat:"):
        cat_id_str = data.split(":", 1)[1]
        try:
            cat_id = int(cat_id_str)
        except ValueError:
            return
        state.set(user_id, "csv_category", cat_id)
        state.set(user_id, "csv_stage", "upload")
        await query.edit_message_text("📁 Upload a CSV file:")
        return

    # ── CSV column mapping ────────────────────────────────
    if data.startswith("csvcol:"):
        if not await require_admin(update):
            return
        try:
            col_idx = int(data.split(":")[1])
        except (ValueError, IndexError):
            return
        headers = state.get(user_id, "csv_headers", [])
        mapping = state.get(user_id, "csv_mapping", {})
        stage = state.get(user_id, "csv_stage")

        if stage == "map_username":
            mapping["username"] = col_idx
            state.set(user_id, "csv_mapping", mapping)
            state.set(user_id, "csv_stage", "map_password")
            buttons = [[InlineKeyboardButton(h, callback_data=f"csvcol:{i}")] for i, h in enumerate(headers)]
            await query.edit_message_text(
                f"✅ Username: {esc(headers[col_idx])}\n\nWhich column is the <b>password</b>?",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        elif stage == "map_password":
            mapping["password"] = col_idx
            state.set(user_id, "csv_mapping", mapping)
            state.set(user_id, "csv_stage", "map_email")
            buttons = [[InlineKeyboardButton(h, callback_data=f"csvcol:{i}")] for i, h in enumerate(headers)]
            buttons.append([InlineKeyboardButton("⏭️ Skip", callback_data="csvskip:email")])
            await query.edit_message_text(
                f"✅ Password: {esc(headers[col_idx])}\n\nWhich column is the <b>email</b>? (or skip)",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        elif stage == "map_email":
            mapping["email"] = col_idx
            state.set(user_id, "csv_mapping", mapping)
            state.set(user_id, "csv_stage", "map_email_password")
            buttons = [[InlineKeyboardButton(h, callback_data=f"csvcol:{i}")] for i, h in enumerate(headers)]
            buttons.append([InlineKeyboardButton("⏭️ Skip", callback_data="csvskip:email_password")])
            await query.edit_message_text(
                f"✅ Email: {esc(headers[col_idx])}\n\nWhich column is the <b>email password</b>? (or skip)",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        elif stage == "map_email_password":
            mapping["email_password"] = col_idx
            state.set(user_id, "csv_mapping", mapping)
            state.set(user_id, "csv_stage", "map_2fa")
            buttons = [
                [InlineKeyboardButton("Yes", callback_data="csvbool:2fa:yes"),
                 InlineKeyboardButton("No", callback_data="csvbool:2fa:no")],
                [InlineKeyboardButton(h, callback_data=f"csvcol:{i}") for i, h in enumerate(headers)],
                [InlineKeyboardButton("⏭️ Skip", callback_data="csvskip:2fa")],
            ]
            await query.edit_message_text(
                f"✅ Email Password: {esc(headers[col_idx])}\n\nIs 2FA a column, or set all to Yes/No?",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        elif stage == "map_2fa":
            mapping["has_2fa"] = col_idx
            state.set(user_id, "csv_mapping", mapping)
            state.set(user_id, "csv_stage", "map_verified")
            buttons = [
                [InlineKeyboardButton("Yes", callback_data="csvbool:verified:yes"),
                 InlineKeyboardButton("No", callback_data="csvbool:verified:no")],
                [InlineKeyboardButton(h, callback_data=f"csvcol:{i}") for i, h in enumerate(headers)],
                [InlineKeyboardButton("⏭️ Skip", callback_data="csvskip:verified")],
            ]
            await query.edit_message_text(
                f"✅ 2FA: {esc(headers[col_idx])}\n\nIs verified a column, or set all to Yes/No?",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        elif stage == "map_verified":
            mapping["is_verified"] = col_idx
            state.set(user_id, "csv_mapping", mapping)
            state.set(user_id, "csv_stage", "map_notes")
            buttons = [[InlineKeyboardButton(h, callback_data=f"csvcol:{i}")] for i, h in enumerate(headers)]
            buttons.append([InlineKeyboardButton("⏭️ Skip", callback_data="csvskip:notes")])
            await query.edit_message_text(
                f"✅ Verified: {esc(headers[col_idx])}\n\nWhich column is <b>notes</b>? (or skip)",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        elif stage == "map_notes":
            mapping["notes"] = col_idx
            state.set(user_id, "csv_mapping", mapping)
            await _csv_show_preview(update, context, user_id, query)
        return

    # ── CSV bool shortcuts (Yes/No for 2FA/verified) ───────
    if data.startswith("csvbool:"):
        if not await require_admin(update):
            return
        parts = data.split(":")
        field = parts[1]
        val = parts[2] == "yes"
        mapping = state.get(user_id, "csv_mapping", {})
        mapping[field] = val
        state.set(user_id, "csv_mapping", mapping)
        if field == "2fa":
            state.set(user_id, "csv_stage", "map_verified")
            headers = state.get(user_id, "csv_headers", [])
            buttons = [
                [InlineKeyboardButton("Yes", callback_data="csvbool:verified:yes"),
                 InlineKeyboardButton("No", callback_data="csvbool:verified:no")],
                [InlineKeyboardButton(h, callback_data=f"csvcol:{i}") for i, h in enumerate(headers)],
                [InlineKeyboardButton("⏭️ Skip", callback_data="csvskip:verified")],
            ]
            await query.edit_message_text(
                f"✅ 2FA: {'All Yes' if val else 'All No'}\n\nIs verified a column, or set all to Yes/No?",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        elif field == "verified":
            state.set(user_id, "csv_stage", "map_notes")
            headers = state.get(user_id, "csv_headers", [])
            buttons = [[InlineKeyboardButton(h, callback_data=f"csvcol:{i}")] for i, h in enumerate(headers)]
            buttons.append([InlineKeyboardButton("⏭️ Skip", callback_data="csvskip:notes")])
            await query.edit_message_text(
                f"✅ Verified: {'All Yes' if val else 'All No'}\n\nWhich column is <b>notes</b>? (or skip)",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        return

    if data.startswith("csvskip:"):
        if not await require_admin(update):
            return
        field = data.split(":")[1]
        stage = state.get(user_id, "csv_stage")
        headers = state.get(user_id, "csv_headers", [])

        if stage == "map_email":
            state.set(user_id, "csv_stage", "map_email_password")
            buttons = [[InlineKeyboardButton(h, callback_data=f"csvcol:{i}")] for i, h in enumerate(headers)]
            buttons.append([InlineKeyboardButton("⏭️ Skip", callback_data="csvskip:email_password")])
            await query.edit_message_text(
                "⏭️ Email skipped\n\nWhich column is the <b>email password</b>? (or skip)",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        elif stage == "map_email_password":
            state.set(user_id, "csv_stage", "map_2fa")
            buttons = [
                [InlineKeyboardButton("Yes", callback_data="csvbool:2fa:yes"),
                 InlineKeyboardButton("No", callback_data="csvbool:2fa:no")],
                [InlineKeyboardButton(h, callback_data=f"csvcol:{i}") for i, h in enumerate(headers)],
                [InlineKeyboardButton("⏭️ Skip", callback_data="csvskip:2fa")],
            ]
            await query.edit_message_text(
                "⏭️ Email password skipped\n\nIs 2FA a column, or set all to Yes/No?",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        elif stage == "map_2fa":
            state.set(user_id, "csv_stage", "map_verified")
            buttons = [
                [InlineKeyboardButton("Yes", callback_data="csvbool:verified:yes"),
                 InlineKeyboardButton("No", callback_data="csvbool:verified:no")],
                [InlineKeyboardButton(h, callback_data=f"csvcol:{i}") for i, h in enumerate(headers)],
                [InlineKeyboardButton("⏭️ Skip", callback_data="csvskip:verified")],
            ]
            await query.edit_message_text(
                "⏭️ 2FA skipped\n\nIs verified a column, or set all to Yes/No?",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        elif stage == "map_verified":
            state.set(user_id, "csv_stage", "map_notes")
            buttons = [[InlineKeyboardButton(h, callback_data=f"csvcol:{i}")] for i, h in enumerate(headers)]
            buttons.append([InlineKeyboardButton("⏭️ Skip", callback_data="csvskip:notes")])
            await query.edit_message_text(
                "⏭️ Verified skipped\n\nWhich column is <b>notes</b>? (or skip)",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        elif stage == "map_notes":
            await _csv_show_preview(update, context, user_id, query)
        return

    # ── CSV confirm/cancel ─────────────────────────────────
    if data == "csvconfirm":
        if not await require_admin(update):
            return
        headers = state.pop(user_id, "csv_headers")
        csv_data = state.pop(user_id, "csv_data")
        mapping = state.pop(user_id, "csv_mapping")
        cat_id = state.pop(user_id, "csv_category")
        state.pop(user_id, "csv_stage", None)
        if not headers or not csv_data or not mapping:
            await query.edit_message_text("❌ CSV import data lost. Try again.")
            return
        accounts = build_accounts_from_csv(headers, csv_data, mapping)
        if not accounts:
            await query.edit_message_text("📭 No valid accounts found in CSV.")
            return
        result = add_accounts_bulk(accounts, cat_id)
        cat_name = get_category_name(cat_id) or "—"
        msg = f"📥 CSV import: {result['added']} added, {result['skipped']} skipped in {cat_name}"
        await query.edit_message_text(msg)
        await notify_admin(context, f"📥 CSV import: {result['added']} added, {result['skipped']} skipped in {cat_name}")
        return

    if data == "csvcancel":
        for key in ("csv_headers", "csv_data", "csv_mapping", "csv_category", "csv_stage"):
            state.pop(user_id, key, None)
        await query.edit_message_text("❌ CSV import cancelled.")
        return

    # ── Bulk delete confirm/cancel ─────────────────────────
    if data == "bulkdelconfirm":
        if not await require_admin(update):
            return
        raw = state.pop(user_id, "bulk_delete_input", "")
        state.pop(user_id, "bulk_delete_mode", None)
        raw = raw.strip()
        deleted = 0
        if raw.isdigit():
            success = delete_account(int(raw))
            if success:
                deleted = 1
        elif "," in raw:
            ids = []
            for part in raw.split(","):
                part = part.strip()
                if part.isdigit():
                    ids.append(int(part))
            if ids:
                from database import delete_accounts_by_ids
                deleted = delete_accounts_by_ids(ids)
        else:
            from database.categories import get_category_id_by_name
            cat_id = get_category_id_by_name(raw)
            if cat_id:
                from database import delete_accounts_in_category
                deleted = delete_accounts_in_category(cat_id)
        await query.edit_message_text(f"✅ Deleted {deleted} account(s).")
        return

    if data == "bulkdelcancel":
        state.pop(user_id, "bulk_delete_input", None)
        state.pop(user_id, "bulk_delete_mode", None)
        await query.edit_message_text("❌ Bulk delete cancelled.")
        return

    # ── Category delete confirm/cancel ─────────────────────
    if data.startswith("delcatconfirm:"):
        if not await require_admin(update):
            return
        cat_id_str = data.split(":", 1)[1]
        state.pop(user_id, "delete_category_confirm", None)
        try:
            cat_id = int(cat_id_str)
        except ValueError:
            return
        cat_name = get_category_name(cat_id) or "—"
        success, msg = delete_category(cat_name)
        await query.edit_message_text(msg)
        return

    if data == "delcatcancel":
        state.pop(user_id, "delete_category_confirm", None)
        await query.edit_message_text("❌ Category deletion cancelled.")
        return

    # ── Search ─────────────────────────────────────────────
    if data.startswith("search:"):
        if not await require_seller(update):
            return
        search_type = data.split(":", 1)[1]
        await handle_search_type(update, context, search_type)
        return

    if data.startswith("searchcat:"):
        if not await require_seller(update):
            return
        cat_id_str = data.split(":", 1)[1]
        await handle_search_category(update, context, cat_id_str)
        return

    if data.startswith("searchstatus:"):
        if not await require_seller(update):
            return
        status_val = data.split(":", 1)[1]
        await handle_search_status(update, context, status_val)
        return


async def _csv_show_preview(update, context, user_id, query):
    headers = state.get(user_id, "csv_headers", [])
    csv_data = state.get(user_id, "csv_data", [])
    mapping = state.get(user_id, "csv_mapping", {})
    state.set(user_id, "csv_stage", "preview")
    accounts = build_accounts_from_csv(headers, csv_data, mapping)
    if not accounts:
        await query.edit_message_text("📭 No valid accounts found in CSV with the selected mapping.")
        return
    preview = accounts[:3]
    map_desc = []
    if "username" in mapping:
        map_desc.append(f"Username: {headers[mapping['username']]}")
    if "password" in mapping:
        map_desc.append(f"Password: {headers[mapping['password']]}")
    if "email" in mapping:
        map_desc.append(f"Email: {headers[mapping['email']]}")
    if "email_password" in mapping:
        map_desc.append(f"Email Pass: {headers[mapping['email_password']]}")
    if isinstance(mapping.get("has_2fa"), int):
        map_desc.append(f"2FA: {headers[mapping['has_2fa']]}")
    elif mapping.get("has_2fa") is True:
        map_desc.append("2FA: All Yes")
    elif mapping.get("has_2fa") is False:
        map_desc.append("2FA: All No")
    if isinstance(mapping.get("is_verified"), int):
        map_desc.append(f"Verified: {headers[mapping['is_verified']]}")
    elif mapping.get("is_verified") is True:
        map_desc.append("Verified: All Yes")
    elif mapping.get("is_verified") is False:
        map_desc.append("Verified: All No")
    if "notes" in mapping:
        map_desc.append(f"Notes: {headers[mapping['notes']]}")
    text = f"<b>CSV Preview ({len(accounts)} accounts):</b>\n\n"
    text += "<b>Mapping:</b> " + " | ".join(map_desc) + "\n\n"
    for acc in preview:
        text += f"• {esc(acc.get('username', ''))} | {esc(str(acc.get('password', ''))[:4])}***"
        if acc.get("email"):
            text += f" | {esc(acc['email'])}"
        text += "\n"
    if len(accounts) > 3:
        text += f"\n... and {len(accounts) - 3} more"
    await query.edit_message_text(
        text, parse_mode="HTML",
        reply_markup=confirm_keyboard("csvconfirm", "csvcancel"),
    )


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
