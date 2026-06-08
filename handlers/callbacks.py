import logging
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.permissions import require_seller, require_admin, get_user_role
from core.state import state
from core.format import esc, fmt_compact
from core.keyboards import (
    main_menu_keyboard, add_menu_keyboard, settings_keyboard,
    confirm_keyboard, pagination_keyboard, category_keyboard,
    yes_no_keyboard, sell_accounts_keyboard,
)
from database import (
    list_categories, get_category_name, delete_account, delete_category,
    list_accounts, count_accounts, get_account_by_id, get_category_id_by_name,
    sell_account, mark_payment, void_sale, get_sale_by_id, get_sales, count_sales,
    add_accounts_bulk, export_accounts_csv,
)
from database.sellers import get_seller_by_user_id
from utils.csv_utils import build_accounts_from_csv
from handlers.preview import handle_preview_category
from handlers.search import handle_search_type
from handlers.reports import handle_report_period
from utils.notifications import (
    notify_admin, fmt_payment_notification, fmt_void_notification,
)
import config

logger = logging.getLogger(__name__)

PAGE_SIZE = 10
MAX_MSG_LEN = 4000


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
    if "has_2fa" in mapping:
        map_desc.append(f"2FA: {headers[mapping['has_2fa']]}")
    if "is_verified" in mapping:
        map_desc.append(f"Verified: {headers[mapping['is_verified']]}")
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
        state.pop(user_id, "add_username", None)
        state.pop(user_id, "add_password", None)
        state.pop(user_id, "add_email", None)
        state.pop(user_id, "add_email_password", None)
        state.pop(user_id, "add_2fa", None)
        state.pop(user_id, "add_verified", None)
        state.pop(user_id, "add_notes", None)
        state.pop(user_id, "add_category_id", None)
        state.pop(user_id, "add_stage", None)
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

    # ── Sell flow ──────────────────────────────────────────
    if data == "menu:sell":
        if not await require_seller(update):
            return
        seller = get_seller_by_user_id(user_id)
        if not seller:
            await query.edit_message_text("You are not registered as a seller.")
            return
        accounts = list_accounts(limit=20, status="active")
        if not accounts:
            await query.edit_message_text("📭 No available accounts to sell.")
            return
        state.set(user_id, "sell_stage", "select_account")
        kb = sell_accounts_keyboard(accounts, "sellselect")
        await query.edit_message_text("💰 Select an account to sell:", reply_markup=kb)
        return

    if data.startswith("sellselect:") or data.startswith("quick sell:"):
        if not await require_seller(update):
            return
        parts = data.split(":")
        try:
            account_id = int(parts[1])
        except ValueError:
            return
        account = get_account_by_id(account_id)
        if not account:
            await query.edit_message_text("🔍 Account not found.")
            return
        state.set(user_id, "sell_account_id", account_id)
        state.set(user_id, "sell_stage", "buyer")
        await query.edit_message_text(
            f"Account: {esc(account['username'])}\n\n👤 Enter buyer name:"
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
        tags = state.pop(user_id, "sell_tags")
        state.pop(user_id, "sell_stage", None)
        if not account_id or not buyer:
            await query.edit_message_text("❌ Sell cancelled — missing data.")
            return
        success, msg, sale_id = sell_account(account_id, seller["id"], buyer, price, tags=tags)
        if success:
            from core.format import fmt_receipt
            sale = get_sale_by_id(sale_id)
            receipt = fmt_receipt(sale)
            await query.edit_message_text(receipt, parse_mode="HTML")
            await notify_admin(context, f"💰 New sale! #{sale_id} — {buyer} — ₹{price:.0f} — by {seller['name']}")
            if price >= config.HIGH_VALUE_THRESHOLD:
                await notify_admin(context, f"🔥 High-value sale! #{sale_id} — ₹{price:.0f} from {buyer} — by {seller['name']}")
        else:
            await query.edit_message_text(f"❌ {msg}")
        return

    if data == "sellcancel":
        state.pop(user_id, "sell_account_id", None)
        state.pop(user_id, "sell_buyer", None)
        state.pop(user_id, "sell_price", None)
        state.pop(user_id, "sell_tags", None)
        state.pop(user_id, "sell_stage", None)
        await query.edit_message_text("❌ Sale cancelled.")
        return

    # ── Bulk sell ──────────────────────────────────────────
    if data.startswith("bulksellselect:"):
        if not await require_seller(update):
            return
        parts = data.split(":")
        try:
            account_id = int(parts[1])
        except ValueError:
            return
        selected = state.get(user_id, "bulksell_selected", [])
        if account_id in selected:
            selected.remove(account_id)
        else:
            selected.append(account_id)
        state.set(user_id, "bulksell_selected", selected)
        accounts = list_accounts(limit=20, status="active")
        buttons = []
        for acc in accounts:
            mark = "✅" if acc["id"] in selected else "  "
            buttons.append([
                InlineKeyboardButton(
                    f"{mark} #{acc['id']} | {acc['username']}",
                    callback_data=f"bulksellselect:{acc['id']}",
                )
            ])
        buttons.append([
            InlineKeyboardButton(
                f"✅ Confirm ({len(selected)} selected)",
                callback_data="bulksellconfirm",
            ),
            InlineKeyboardButton("❌ Cancel", callback_data="bulksellcancel"),
        ])
        kb = InlineKeyboardMarkup(buttons)
        await query.edit_message_text(
            f"Selected: {len(selected)} accounts\nTap to toggle, then confirm:",
            reply_markup=kb,
        )
        return

    if data == "bulksellconfirm":
        if not await require_seller(update):
            return
        seller = get_seller_by_user_id(user_id)
        if not seller:
            await query.edit_message_text("⚠️ You are not registered as a seller.")
            return
        selected = state.pop(user_id, "bulksell_selected", [])
        buyer = state.pop(user_id, "bulksell_buyer")
        price = state.pop(user_id, "bulksell_price", 0)
        state.pop(user_id, "bulksell_stage", None)
        if not selected or not buyer:
            await query.edit_message_text("❌ Bulk sell cancelled — no accounts selected.")
            return
        from database import bulk_sell_accounts
        result = bulk_sell_accounts(selected, seller["id"], buyer, price)
        await query.edit_message_text(
            f"✅ Bulk sell complete: {result['added']} sold, {result['skipped']} skipped"
        )
        await notify_admin(context, f"💰 Bulk sell: {result['added']} accounts to {buyer} — ₹{price:.0f} each — by {seller['name']}")
        return

    if data == "bulksellcancel":
        state.pop(user_id, "bulksell_selected", None)
        state.pop(user_id, "bulksell_buyer", None)
        state.pop(user_id, "bulksell_price", None)
        state.pop(user_id, "bulksell_stage", None)
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
        text = f"<b>📈 Sales (1/{total_pages})</b>\n\n"
        for s in sales:
            text += (
                f"• #{s['id']} | {esc(s['buyer_name'])} | "
                f"₹{s['price']:.0f} | {esc(s['payment_status'])} | "
                f"{esc(dict(s).get('seller_name', '—'))}\n"
            )
        filter_buttons = [
            InlineKeyboardButton("All", callback_data="salesfilter:all"),
            InlineKeyboardButton("Pending", callback_data="salesfilter:pending"),
            InlineKeyboardButton("Paid", callback_data="salesfilter:paid"),
        ]
        nav_buttons = []
        if 1 > 1:
            nav_buttons.append(InlineKeyboardButton("⬅️", callback_data="salespage:0"))
        nav_buttons.append(InlineKeyboardButton(f"1/{total_pages}", callback_data="noop"))
        if total_pages > 1:
            nav_buttons.append(InlineKeyboardButton("➡️", callback_data="salespage:2"))
        kb = InlineKeyboardMarkup([filter_buttons, nav_buttons])
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return

    # ── List accounts ──────────────────────────────────────
    if data == "menu:list":
        if not await require_seller(update):
            return
        state.set(user_id, "list_page", 1)
        state.set(user_id, "list_filter", None)
        total = count_accounts()
        if total == 0:
            await query.edit_message_text("📭 No accounts found.")
            return
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        accounts = list_accounts(limit=PAGE_SIZE, offset=0)
        text = f"<b>📋 Accounts (1/{total_pages})</b>\n\n"
        for acc in accounts:
            text += fmt_compact(acc) + "\n"
        filter_row = [
            InlineKeyboardButton("All", callback_data="listfilter:all"),
            InlineKeyboardButton("Available", callback_data="listfilter:available"),
            InlineKeyboardButton("Sold", callback_data="listfilter:sold"),
        ]
        cat_row = [
            InlineKeyboardButton("By Category", callback_data="listfiltercat"),
        ]
        nav_row = []
        if 1 > 1:
            nav_row.append(InlineKeyboardButton("⬅️", callback_data="accountpage:0"))
        nav_row.append(InlineKeyboardButton(f"1/{total_pages}", callback_data="noop"))
        if total_pages > 1:
            nav_row.append(InlineKeyboardButton("➡️", callback_data="accountpage:2"))
        kb = InlineKeyboardMarkup([filter_row, cat_row, nav_row])
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
        total = count_accounts(category_id=cat_id)
        if total == 0:
            await query.edit_message_text("📭 No accounts in this category.")
            return
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        accounts = list_accounts(limit=PAGE_SIZE, offset=0, category_id=cat_id)
        cat_name = get_category_name(cat_id) or "—"
        text = f"<b>📋 {cat_name} (1/{total_pages})</b>\n\n"
        for acc in accounts:
            text += fmt_compact(acc) + "\n"
        filter_row = [
            InlineKeyboardButton("All", callback_data="listfilter:all"),
            InlineKeyboardButton("Available", callback_data="listfilter:available"),
            InlineKeyboardButton("Sold", callback_data="listfilter:sold"),
        ]
        cat_row = [
            InlineKeyboardButton("By Category", callback_data="listfiltercat"),
        ]
        nav_row = []
        if 1 > 1:
            nav_row.append(InlineKeyboardButton("⬅️", callback_data="accountpage:0"))
        nav_row.append(InlineKeyboardButton(f"1/{total_pages}", callback_data="noop"))
        if total_pages > 1:
            nav_row.append(InlineKeyboardButton("➡️", callback_data="accountpage:2"))
        kb = InlineKeyboardMarkup([filter_row, cat_row, nav_row])
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return

    # ── Search ─────────────────────────────────────────────
    if data == "menu:search":
        state.set(user_id, "search_stage", "type")
        from core.keyboards import search_type_keyboard
        await query.edit_message_text("Select search type:", reply_markup=search_type_keyboard())
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
        from core.keyboards import report_period_keyboard
        await query.edit_message_text("📊 Select a period:", reply_markup=report_period_keyboard())
        return

    # ── Inventory ──────────────────────────────────────────
    if data == "menu:inventory":
        if not await require_seller(update):
            return
        from database.accounts import count_accounts as ca
        from database.sales import get_sales_summary
        cats = list_categories()
        available = ca(status="active")
        sold = ca(used=True)
        banned = ca(status="banned")
        locked = ca(status="locked")
        restricted = ca(status="restricted")
        summary = get_sales_summary()
        text = "<b>📦 Inventory Overview</b>\n\n"
        text += f"🟢 Active: {available}\n"
        text += f"🔴 Sold: {sold}\n"
        text += f"⛔ Banned: {banned}\n"
        text += f"🔒 Locked: {locked}\n"
        text += f"⚠️ Restricted: {restricted}\n"
        text += f"💰 Total revenue: ₹{summary['total_revenue']:.0f}\n\n"
        text += "<b>By Category:</b>\n"
        for cat in cats:
            cat_available = ca(category_id=cat["id"], status="active")
            cat_sold = ca(category_id=cat["id"], used=True)
            text += f"• {esc(cat['name'])}: {cat_available} active, {cat_sold} sold\n"
        await query.edit_message_text(_truncate(text), parse_mode="HTML")
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

    # ── Preview category selection ─────────────────────────
    if data.startswith("previewcat:"):
        cat_id_str = data.split(":", 1)[1]
        if cat_id_str != "all":
            try:
                int(cat_id_str)
            except ValueError:
                return
        await handle_preview_category(update, context, cat_id_str)
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
            buttons = [[InlineKeyboardButton(h, callback_data=f"csvcol:{i}")] for i, h in enumerate(headers)]
            buttons.append([InlineKeyboardButton("⏭️ Skip", callback_data="csvskip:2fa")])
            await query.edit_message_text(
                f"✅ Email Password: {esc(headers[col_idx])}\n\nWhich column is the <b>2FA status</b>? (or skip)",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        elif stage == "map_2fa":
            mapping["has_2fa"] = col_idx
            state.set(user_id, "csv_mapping", mapping)
            state.set(user_id, "csv_stage", "map_verified")
            buttons = [[InlineKeyboardButton(h, callback_data=f"csvcol:{i}")] for i, h in enumerate(headers)]
            buttons.append([InlineKeyboardButton("⏭️ Skip", callback_data="csvskip:verified")])
            await query.edit_message_text(
                f"✅ 2FA: {esc(headers[col_idx])}\n\nWhich column is the <b>verified status</b>? (or skip)",
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

    if data.startswith("csvskip:"):
        if not await require_admin(update):
            return
        field = data.split(":")[1]
        stage = state.get(user_id, "csv_stage")
        mapping = state.get(user_id, "csv_mapping", {})
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
            buttons = [[InlineKeyboardButton(h, callback_data=f"csvcol:{i}")] for i, h in enumerate(headers)]
            buttons.append([InlineKeyboardButton("⏭️ Skip", callback_data="csvskip:2fa")])
            await query.edit_message_text(
                "⏭️ Email password skipped\n\nWhich column is the <b>2FA status</b>? (or skip)",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        elif stage == "map_2fa":
            state.set(user_id, "csv_stage", "map_verified")
            buttons = [[InlineKeyboardButton(h, callback_data=f"csvcol:{i}")] for i, h in enumerate(headers)]
            buttons.append([InlineKeyboardButton("⏭️ Skip", callback_data="csvskip:verified")])
            await query.edit_message_text(
                "⏭️ 2FA skipped\n\nWhich column is the <b>verified status</b>? (or skip)",
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

    # ── Delete confirm/cancel ──────────────────────────────
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

    # ── Mark paid ──────────────────────────────────────────
    if data.startswith("markpaid:"):
        if not await require_seller(update):
            return
        parts = data.split(":")
        try:
            sale_id = int(parts[1])
        except ValueError:
            return
        sale = get_sale_by_id(sale_id)
        if not sale:
            await query.edit_message_text("🔍 Sale not found.")
            return
        role = get_user_role(user_id)
        if role != "admin" and sale["seller_user_id"] != user_id:
            await query.edit_message_text("⚠️ You can only mark your own sales as paid.")
            return
        new_status = "paid" if sale["payment_status"] == "pending" else "pending"
        mark_payment(sale_id, new_status)
        label = "paid" if new_status == "paid" else "pending"
        await query.edit_message_text(f"✅ Sale #{sale_id} marked as {label}.")
        if new_status == "paid":
            await notify_admin(context, f"✅ Payment received! Sale #{sale_id} — ₹{sale['price']:.0f} from {sale['buyer_name']}")
        return

    # ── Void sale confirm/cancel ───────────────────────────
    if data.startswith("voidconfirm:"):
        if not await require_admin(update):
            return
        parts = data.split(":")
        try:
            sale_id = int(parts[1])
        except ValueError:
            return
        state.pop(user_id, "void_confirm", None)
        success = void_sale(sale_id)
        if success:
            await query.edit_message_text(f"✅ Sale #{sale_id} voided. Account returned to stock.")
            await notify_admin(context, fmt_void_notification(sale_id))
        else:
            await query.edit_message_text("❌ Failed to void sale.")
        return

    if data == "voidcancel":
        state.pop(user_id, "void_confirm", None)
        await query.edit_message_text("❌ Void cancelled.")
        return

    # ── Account pagination ─────────────────────────────────
    if data.startswith("accountpage:"):
        if not await require_seller(update):
            return
        try:
            page = int(data.split(":")[1])
        except ValueError:
            return
        f = state.get(user_id, "list_filter")
        used_val = None
        if f == "available":
            used_val = False
        elif f == "sold":
            used_val = True
        cat_id = None
        if f and f.startswith("cat:"):
            try:
                cat_id = int(f.split(":")[1])
            except ValueError:
                pass
        total = count_accounts(used=used_val, category_id=cat_id)
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = max(1, min(page, total_pages))
        state.set(user_id, "list_page", page)
        accounts = list_accounts(limit=PAGE_SIZE, offset=(page - 1) * PAGE_SIZE, used=used_val, category_id=cat_id)
        text = f"<b>📋 Accounts ({page}/{total_pages})</b>\n\n"
        for acc in accounts:
            text += fmt_compact(acc) + "\n"
        filter_row = [
            InlineKeyboardButton("All", callback_data="listfilter:all"),
            InlineKeyboardButton("Available", callback_data="listfilter:available"),
            InlineKeyboardButton("Sold", callback_data="listfilter:sold"),
        ]
        cat_row = [
            InlineKeyboardButton("By Category", callback_data="listfiltercat"),
        ]
        nav_row = []
        if page > 1:
            nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"accountpage:{page - 1}"))
        nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
        if page < total_pages:
            nav_row.append(InlineKeyboardButton("➡️", callback_data=f"accountpage:{page + 1}"))
        kb = InlineKeyboardMarkup([filter_row, cat_row, nav_row])
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return

    # ── List filter ────────────────────────────────────────
    if data.startswith("listfilter:") and not data.startswith("listfiltercat"):
        if not await require_seller(update):
            return
        f = data.split(":", 1)[1]
        state.set(user_id, "list_filter", f if f != "all" else None)
        state.set(user_id, "list_page", 1)
        cat_id = None
        used_val = None
        if f.startswith("cat:"):
            try:
                cat_id = int(f.split(":")[1])
            except ValueError:
                pass
        elif f == "available":
            used_val = False
        elif f == "sold":
            used_val = True
        total = count_accounts(used=used_val, category_id=cat_id)
        if total == 0:
            await query.edit_message_text("📭 No accounts found.")
            return
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        accounts = list_accounts(limit=PAGE_SIZE, offset=0, used=used_val, category_id=cat_id)
        text = f"<b>📋 Accounts (1/{total_pages})</b>\n\n"
        for acc in accounts:
            text += fmt_compact(acc) + "\n"
        filter_row = [
            InlineKeyboardButton("All", callback_data="listfilter:all"),
            InlineKeyboardButton("Available", callback_data="listfilter:available"),
            InlineKeyboardButton("Sold", callback_data="listfilter:sold"),
        ]
        cat_row = [
            InlineKeyboardButton("By Category", callback_data="listfiltercat"),
        ]
        nav_row = []
        if 1 > 1:
            nav_row.append(InlineKeyboardButton("⬅️", callback_data="accountpage:0"))
        nav_row.append(InlineKeyboardButton(f"1/{total_pages}", callback_data="noop"))
        if total_pages > 1:
            nav_row.append(InlineKeyboardButton("➡️", callback_data="accountpage:2"))
        kb = InlineKeyboardMarkup([filter_row, cat_row, nav_row])
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return

    # ── Sales pagination ───────────────────────────────────
    if data.startswith("salespage:"):
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
        text = f"<b>📈 Sales ({page}/{total_pages})</b>\n\n"
        for s in sales:
            text += (
                f"• #{s['id']} | {esc(s['buyer_name'])} | "
                f"₹{s['price']:.0f} | {esc(s['payment_status'])} | "
                f"{esc(dict(s).get('seller_name', '—'))}\n"
            )
        filter_buttons = [
            InlineKeyboardButton("All", callback_data="salesfilter:all"),
            InlineKeyboardButton("Pending", callback_data="salesfilter:pending"),
            InlineKeyboardButton("Paid", callback_data="salesfilter:paid"),
        ]
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"salespage:{page - 1}"))
        nav_buttons.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"salespage:{page + 1}"))
        kb = InlineKeyboardMarkup([filter_buttons, nav_buttons])
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return

    # ── Sales filter ───────────────────────────────────────
    if data.startswith("salesfilter:"):
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
        text = f"<b>📈 Sales (1/{total_pages})</b>\n\n"
        for s in sales:
            text += (
                f"• #{s['id']} | {esc(s['buyer_name'])} | "
                f"₹{s['price']:.0f} | {esc(s['payment_status'])} | "
                f"{esc(dict(s).get('seller_name', '—'))}\n"
            )
        filter_buttons = [
            InlineKeyboardButton("All", callback_data="salesfilter:all"),
            InlineKeyboardButton("Pending", callback_data="salesfilter:pending"),
            InlineKeyboardButton("Paid", callback_data="salesfilter:paid"),
        ]
        nav_buttons = []
        if 1 > 1:
            nav_buttons.append(InlineKeyboardButton("⬅️", callback_data="salespage:0"))
        nav_buttons.append(InlineKeyboardButton(f"1/{total_pages}", callback_data="noop"))
        if total_pages > 1:
            nav_buttons.append(InlineKeyboardButton("➡️", callback_data="salespage:2"))
        kb = InlineKeyboardMarkup([filter_buttons, nav_buttons])
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return

    # ── Search type ────────────────────────────────────────
    if data.startswith("search:"):
        if not await require_seller(update):
            return
        search_type = data.split(":", 1)[1]
        await handle_search_type(update, context, search_type)
        return

    # ── Report period ──────────────────────────────────────
    if data.startswith("report:"):
        if not await require_admin(update):
            return
        period = data.split(":", 1)[1]
        await handle_report_period(update, context, period)
        return
