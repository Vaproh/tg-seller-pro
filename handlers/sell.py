import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.permissions import require_seller, require_admin, get_user_role
from core.state import state
from core.format import esc, fmt_sale_block, fmt_receipt, _d, _truncate
from core.keyboards import confirm_keyboard
from core.filters import (
    filter_page_keyboard, apply_list_filters, count_from_filter,
    fmt_account_list_page, fmt_account_list_line,
    buyer_keyboard, payment_status_keyboard, parse_filter_state,
    build_filter_state, PAGE_SIZE,
)
from database import (
    sell_account, bulk_sell_accounts, mark_payment, get_sales, count_sales,
    get_sale_by_id, void_sale, list_accounts, count_accounts,
    get_seller_by_user_id, get_buyer_names, set_account_status,
    get_account_by_id,
)
from database.sales import update_sale, create_draft_sale
from utils.notifications import (
    notify_admin, fmt_sale_notification, fmt_payment_notification,
    fmt_high_value_notification, fmt_void_notification,
)
import config

logger = logging.getLogger(__name__)


async def sell_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    user_id = update.effective_user.id
    seller = get_seller_by_user_id(user_id)
    if not seller:
        await update.message.reply_text("⚠️ You are not registered as a seller.")
        return
    state.set(user_id, "sell_filter", "status:available")
    state.set(user_id, "sell_page", 1)
    filter_str = "status:available"
    accounts, total = apply_list_filters(filter_str, limit=PAGE_SIZE, offset=0)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    text = fmt_account_list_page(accounts, 1, total_pages, title="Available Accounts to Sell")
    kb = filter_page_keyboard(
        "sellfilter", 1, total_pages,
        include_available=True, include_sold=False, include_pending=False,
        include_all=False, include_ids=True,
    )
    await update.message.reply_text(_truncate(text), parse_mode="HTML", reply_markup=kb)


async def sell_select_account(update: Update, context: ContextTypes.DEFAULT_TYPE, account_id):
    user_id = update.effective_user.id
    query = update.callback_query
    account = get_account_by_id(account_id)
    if not account or account["status"] != "available":
        await query.edit_message_text("🔍 Account not found or not available.")
        return
    state.set(user_id, "sell_account_id", account_id)
    buyer_names = get_buyer_names()
    if buyer_names:
        kb = buyer_keyboard(buyer_names, "buypick")
        await query.edit_message_text(
            f"💰 Selling: {_d(account)['username']}\n\n👤 Select buyer or type a new one:",
            reply_markup=kb,
        )
    else:
        state.set(user_id, "sell_stage", "buyer")
        await query.edit_message_text(
            f"💰 Selling: {_d(account)['username']}\n\n👤 Enter buyer name:"
        )


async def bulksell_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    user_id = update.effective_user.id
    seller = get_seller_by_user_id(user_id)
    if not seller:
        await update.message.reply_text("⚠️ You are not registered as a seller.")
        return
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👆 Select accounts", callback_data="bulksellmode:select"),
            InlineKeyboardButton("🔢 Enter number", callback_data="bulksellmode:number"),
        ],
    ])
    await update.message.reply_text(
        "💰 How would you like to bulk sell?",
        reply_markup=kb,
    )


async def sales_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    seller = get_seller_by_user_id(user_id) if role != "admin" else None
    seller_id = seller["id"] if seller else None
    state.set(user_id, "sales_page", 1)
    state.set(user_id, "sales_filter", None)
    total = count_sales(seller_id=seller_id)
    if total == 0:
        await update.message.reply_text("📭 No sales found.")
        return
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    sales = get_sales(limit=PAGE_SIZE, offset=0, seller_id=seller_id)
    text = _fmt_sales_page(sales, 1, total_pages)
    kb = _sales_keyboard(1, total_pages)
    await update.message.reply_text(_truncate(text), parse_mode="HTML", reply_markup=kb)


async def sale_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    args = context.args
    if not args:
        await update.message.reply_text("📝 Usage: /sale <sale_id>")
        return
    try:
        sale_id = int(args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Invalid sale ID.")
        return
    sale = get_sale_by_id(sale_id)
    if not sale:
        await update.message.reply_text("🔍 Sale not found.")
        return
    from core.keyboards import sale_actions_keyboard
    await update.message.reply_text(
        fmt_sale_block(sale), parse_mode="HTML",
        reply_markup=sale_actions_keyboard(sale_id),
    )


async def markpaid_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    seller = get_seller_by_user_id(user_id) if role != "admin" else None
    seller_id = seller["id"] if seller else None
    pending = get_sales(limit=50, seller_id=seller_id, status="pending")
    if not pending:
        await update.message.reply_text("📭 No pending payments.")
        return
    buttons = []
    for s in pending:
        sd = _d(s)
        sale_code = sd.get("sale_code", f"#{sd.get('id', '')}")
        buttons.append([
            InlineKeyboardButton(
                f"{sale_code} | {sd.get('buyer_name')} | ₹{sd.get('price', 0):.0f}",
                callback_data=f"markpaid:{sd.get('id')}",
            )
        ])
    kb = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("💳 Select a sale to mark as paid:", reply_markup=kb)


async def voidsale_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    args = context.args
    if not args:
        await update.message.reply_text("📝 Usage: /voidsale <id,id,...>")
        return
    ids = [x.strip() for x in args[0].split(",") if x.strip()]
    valid, invalid = [], []
    for id_str in ids:
        try:
            sale_id = int(id_str)
        except ValueError:
            invalid.append(id_str)
            continue
        sale = get_sale_by_id(sale_id)
        if not sale:
            invalid.append(id_str)
            continue
        sale_code = _d(sale).get("sale_code", f"#{sale_id}")
        void_sale(sale_id)
        valid.append(sale_code)
    parts = []
    if valid:
        parts.append(f"♻️ Voided: {', '.join(valid)}")
    if invalid:
        parts.append(f"⚠️ Not found: {', '.join(invalid)}")
    await update.message.reply_text("\n".join(parts))


async def marksold_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    args = context.args
    if not args:
        await update.message.reply_text("📝 Usage: /marksold <id,id,...>")
        return
    ids = [x.strip() for x in args[0].split(",") if x.strip()]
    valid, invalid = [], []
    for id_str in ids:
        try:
            account_id = int(id_str)
        except ValueError:
            invalid.append(id_str)
            continue
        account = get_account_by_id(account_id)
        if not account:
            invalid.append(id_str)
            continue
        set_account_status(account_id, "sold")
        valid.append(account_id)
    parts = []
    if valid:
        parts.append(f"🔴 Sold: {', '.join(str(i) for i in valid)}")
    if invalid:
        parts.append(f"⚠️ Not found: {', '.join(invalid)}")
    await update.message.reply_text("\n".join(parts))


async def markunsold_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    args = context.args
    if not args:
        await update.message.reply_text("📝 Usage: /markunsold <id,id,...>")
        return
    ids = [x.strip() for x in args[0].split(",") if x.strip()]
    valid, invalid = [], []
    for id_str in ids:
        try:
            account_id = int(id_str)
        except ValueError:
            invalid.append(id_str)
            continue
        account = get_account_by_id(account_id)
        if not account:
            invalid.append(id_str)
            continue
        set_account_status(account_id, "available")
        valid.append(account_id)
    parts = []
    if valid:
        parts.append(f"🟢 Available: {', '.join(str(i) for i in valid)}")
    if invalid:
        parts.append(f"⚠️ Not found: {', '.join(invalid)}")
    await update.message.reply_text("\n".join(parts))


async def markpendingpayment_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    args = context.args
    if not args:
        await update.message.reply_text("📝 Usage: /markpendingpayment <id,id,...>")
        return
    ids = [x.strip() for x in args[0].split(",") if x.strip()]
    valid, invalid = [], []
    for id_str in ids:
        try:
            account_id = int(id_str)
        except ValueError:
            invalid.append(id_str)
            continue
        account = get_account_by_id(account_id)
        if not account:
            invalid.append(id_str)
            continue
        set_account_status(account_id, "pending_payment")
        valid.append(account_id)
    parts = []
    if valid:
        parts.append(f"🟡 Pending: {', '.join(str(i) for i in valid)}")
    if invalid:
        parts.append(f"⚠️ Not found: {', '.join(invalid)}")
    await update.message.reply_text("\n".join(parts))


def _fmt_sales_page(sales, page, total_pages):
    text = f"<b>📈 Sales  page {page}/{total_pages}</b>\n\n"
    for s in sales:
        sd = _d(s)
        ps = sd.get("payment_status", "pending")
        ps_emoji = "✅" if ps == "paid" else "🟡" if ps == "pending" else "⚪"
        sale_code = sd.get("sale_code", f"#{sd.get('id', '')}")
        text += (
            f"• <b>{sale_code}</b> | {esc(sd.get('buyer_name'))} | "
            f"₹{sd.get('price', 0):.0f} | {ps_emoji} {esc(ps)} | "
            f"{esc(sd.get('seller_name', '—'))}\n"
        )
    if not sales:
        text += "📭 No sales found."
    return text


def _sales_keyboard(page, total_pages, prefix="salesfilter"):
    filter_row = [
        InlineKeyboardButton("📋 All", callback_data=f"{prefix}:all"),
        InlineKeyboardButton("🟡 Pending", callback_data=f"{prefix}:pending"),
        InlineKeyboardButton("✅ Paid", callback_data=f"{prefix}:paid"),
    ]
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"{prefix}page:{page - 1}"))
    nav_row.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("➡️", callback_data=f"{prefix}page:{page + 1}"))
    return InlineKeyboardMarkup([filter_row, nav_row])


async def editsale_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    args = context.args
    if not args:
        await update.message.reply_text("📝 Usage: /editsale <id,id,...>")
        return
    ids = [x.strip() for x in args[0].split(",") if x.strip()]
    raw_ids = []
    for id_str in ids:
        try:
            raw_ids.append(int(id_str))
        except ValueError:
            pass
    if not raw_ids:
        await update.message.reply_text("⚠️ No valid IDs.")
        return
    user_id = update.effective_user.id
    seller = get_seller_by_user_id(user_id)
    seller_id = seller["id"] if seller else None
    valid_sales = []
    invalid_ids = []
    created_drafts = []
    for rid in raw_ids:
        sale = get_sale_by_id(rid)
        if sale:
            valid_sales.append(_d(sale))
            continue
        account = get_account_by_id(rid)
        if account and _d(account).get("status") in ("sold", "pending_payment"):
            draft_id = create_draft_sale(rid, seller_id)
            if draft_id:
                sale = get_sale_by_id(draft_id)
                if sale:
                    valid_sales.append(_d(sale))
                    created_drafts.append(rid)
                else:
                    invalid_ids.append(rid)
            else:
                invalid_ids.append(rid)
        else:
            invalid_ids.append(rid)
    if not valid_sales:
        await update.message.reply_text(f"⚠️ Not found: {', '.join(str(i) for i in invalid_ids)}")
        return
    state.set(user_id, "editsale_ids", [s["id"] for s in valid_sales])
    state.set(user_id, "editsale_pending", {})
    text = _editsale_summary(valid_sales, invalid_ids, created_drafts)
    kb = _editsale_field_keyboard()
    await update.message.reply_text(_truncate(text), parse_mode="HTML", reply_markup=kb)


def _editsale_summary(sales, invalid_ids=None, created_drafts=None):
    text = "<b>✏️ Editing sales:</b>\n\n"
    for s in sales:
        ps = s.get("payment_status", "pending")
        ps_emoji = "✅" if ps == "paid" else "🟡"
        buyer = esc(s.get("buyer_name")) or "—"
        price = s.get("price", 0) or 0
        sale_code = s.get("sale_code", f"#{s.get('id', '')}")
        text += (
            f"• <b>{sale_code}</b> | {buyer} | "
            f"₹{price:.0f} | {ps_emoji} {esc(ps)}\n"
        )
    if created_drafts:
        text += f"\n📝 Created draft sale for account(s): {', '.join(str(i) for i in created_drafts)}"
    if invalid_ids:
        text += f"\n⚠️ Not found: {', '.join(str(i) for i in invalid_ids)}"
    return text


def _editsale_field_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👤 Buyer", callback_data="editsale:field:buyer"),
            InlineKeyboardButton("💰 Price", callback_data="editsale:field:price"),
        ],
        [
            InlineKeyboardButton("📦 Status", callback_data="editsale:field:status"),
            InlineKeyboardButton("📝 Notes", callback_data="editsale:field:notes"),
        ],
        [
            InlineKeyboardButton("✅ Done", callback_data="editsale:done"),
            InlineKeyboardButton("❌ Cancel", callback_data="editsale:cancel"),
        ],
    ])
