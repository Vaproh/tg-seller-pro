from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.permissions import require_seller, require_admin
from core.state import state
from core.format import esc, _d, _truncate, code_id, code_username
from core.keyboards import confirm_keyboard, category_keyboard
from core.filters import (
    filter_page_keyboard, apply_list_filters, count_from_filter,
    fmt_account_list_page, parse_filter_state, build_filter_state,
    parse_id_list, buyer_keyboard, payment_status_keyboard,
    fmt_account_list_line, category_keyboard_with_all, PAGE_SIZE,
)
from database import (
    list_categories, get_category_name, delete_account, delete_category,
    list_accounts, count_accounts, get_account_by_id,
    set_account_status, get_seller_by_user_id,
    get_available_accounts_for_category,
)
from database.sales import get_sales_summary
from telegram.error import BadRequest


async def try_handle(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str, user_id: int) -> bool:
    query = update.callback_query

    if data == "menu:list":
        if not await require_seller(update):
            return True
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
        return True

    if data.startswith("listfilter:") and not data.startswith("listfiltercat") and not data.startswith("listfilterids") and not data.startswith("listfilterpage:"):
        if not await require_seller(update):
            return True
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
        return True

    if data == "listfiltercat":
        if not await require_seller(update):
            return True
        kb = category_keyboard("listfiltercatpick")
        if not kb:
            await query.edit_message_text("📭 No categories found.")
            return True
        await query.edit_message_text("📂 Select a category:", reply_markup=kb)
        return True

    if data.startswith("listfiltercatpick:"):
        if not await require_seller(update):
            return True
        cat_id_str = data.split(":", 1)[1]
        try:
            cat_id = int(cat_id_str)
        except ValueError:
            return True
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
        return True

    if data == "listfilterids":
        if not await require_seller(update):
            return True
        state.set(user_id, "list_ids_input", True)
        await query.edit_message_text("🔢 Enter account IDs (comma-separated):")
        return True

    if data.startswith("listfilterpage:"):
        if not await require_seller(update):
            return True
        try:
            page = int(data.split(":")[1])
        except ValueError:
            return True
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
        try:
            await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        except BadRequest:
            pass
        return True

    if data.startswith("delfilter:") and not data.startswith("delfiltercat") and not data.startswith("delfilterids") and not data.startswith("delfilterpage:"):
        if not await require_admin(update):
            return True
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
        return True

    if data == "delfiltercat":
        if not await require_admin(update):
            return True
        kb = category_keyboard("delfiltercatpick")
        if not kb:
            await query.edit_message_text("📭 No categories found.")
            return True
        await query.edit_message_text("📂 Select a category:", reply_markup=kb)
        return True

    if data.startswith("delfiltercatpick:"):
        if not await require_admin(update):
            return True
        cat_id_str = data.split(":", 1)[1]
        try:
            cat_id = int(cat_id_str)
        except ValueError:
            return True
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
        return True

    if data == "delfilterids":
        if not await require_admin(update):
            return True
        state.set(user_id, "del_ids_input", True)
        await query.edit_message_text("🔢 Enter account IDs to delete (comma-separated):")
        return True

    if data.startswith("delfilterpage:"):
        if not await require_admin(update):
            return True
        try:
            page = int(data.split(":")[1])
        except ValueError:
            return True
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
        try:
            await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        except BadRequest:
            pass
        return True

    if data.startswith("delsingle:"):
        if not await require_admin(update):
            return True
        try:
            account_id = int(data.split(":")[1])
        except ValueError:
            return True
        account = get_account_by_id(account_id)
        if not account:
            await query.edit_message_text("🔍 Account not found.")
            return True
        state.set(user_id, "delete_confirm", account_id)
        await query.edit_message_text(
            f"⚠️ Delete account {code_id(account_id)} ({code_username(_d(account)['username'])})?",
            reply_markup=confirm_keyboard(f"delconfirm:{account_id}", "delcancel"),
        )
        return True

    if data.startswith("delconfirm:"):
        if not await require_admin(update):
            return True
        parts = data.split(":")
        try:
            account_id = int(parts[1])
        except ValueError:
            return True
        state.pop(user_id, "delete_confirm", None)
        success = delete_account(account_id)
        if success:
            await query.edit_message_text(f"✅ Account {code_id(account_id)} deleted.")
        else:
            await query.edit_message_text("❌ Failed to delete account.")
        return True

    if data == "delcancel":
        state.pop(user_id, "delete_confirm", None)
        await query.edit_message_text("❌ Deletion cancelled.")
        return True

    if data == "menu:inventory":
        if not await require_seller(update):
            return True
        from handlers.inventory import inventory_cmd
        state.set(user_id, "inv_filter", None)
        state.set(user_id, "inv_page", 1)
        cats = list_categories()
        if not cats:
            await query.edit_message_text("📭 No categories found.")
            return True
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
        return True

    if data.startswith("invfilter:") and not data.startswith("invfiltercat") and not data.startswith("invfilterpage:"):
        if not await require_seller(update):
            return True
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
        return True

    if data == "invfiltercat":
        if not await require_seller(update):
            return True
        kb = category_keyboard("invfiltercatpick")
        if not kb:
            await query.edit_message_text("📭 No categories found.")
            return True
        await query.edit_message_text("📂 Select a category:", reply_markup=kb)
        return True

    if data.startswith("invfiltercatpick:"):
        if not await require_seller(update):
            return True
        cat_id_str = data.split(":", 1)[1]
        try:
            cat_id = int(cat_id_str)
        except ValueError:
            return True
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
        return True

    if data.startswith("invfilterpage:"):
        if not await require_seller(update):
            return True
        try:
            page = int(data.split(":")[1])
        except ValueError:
            return True
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
        try:
            await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        except BadRequest:
            pass
        return True

    if data.startswith("markstatus:"):
        if not await require_seller(update):
            return True
        parts = data.split(":", 2)
        try:
            account_id = int(parts[1])
            new_status = parts[2]
        except (ValueError, IndexError):
            return True
        if new_status not in ("available", "sold", "pending_payment"):
            return True
        success = set_account_status(account_id, new_status)
        if success:
            emoji = {"available": "🟢", "sold": "🔴", "pending_payment": "🟡"}.get(new_status, "⚪")
            await query.edit_message_text(f"✅ Account {code_id(account_id)} marked as {emoji} {new_status}.")
        else:
            await query.edit_message_text("❌ Failed to update status.")
        return True

    if data == "bulkdelconfirm":
        if not await require_admin(update):
            return True
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
        return True

    if data == "bulkdelcancel":
        state.pop(user_id, "bulk_delete_input", None)
        state.pop(user_id, "bulk_delete_mode", None)
        await query.edit_message_text("❌ Bulk delete cancelled.")
        return True

    if data.startswith("delcatconfirm:"):
        if not await require_admin(update):
            return True
        cat_id_str = data.split(":", 1)[1]
        state.pop(user_id, "delete_category_confirm", None)
        try:
            cat_id = int(cat_id_str)
        except ValueError:
            return True
        cat_name = get_category_name(cat_id) or "—"
        success, msg = delete_category(cat_name)
        await query.edit_message_text(msg)
        return True

    if data == "delcatcancel":
        state.pop(user_id, "delete_category_confirm", None)
        await query.edit_message_text("❌ Category deletion cancelled.")
        return True

    return False
