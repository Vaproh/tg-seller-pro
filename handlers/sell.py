from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.permissions import require_seller, require_admin, get_user_role
from core.state import state
from core.format import esc, code, code_id, fmt_sale_block, _d, _truncate
from core.keyboards import confirm_keyboard, sell_select_keyboard
from core.filters import (
    apply_list_filters,
    fmt_account_list_line,
    sale_actions_keyboard,
    PAGE_SIZE,
)
from database import (
    sell_account, get_sales, count_sales,
    get_sale_by_id, void_sale,
    get_seller_by_user_id, set_account_status,
    get_account_by_id,
)
from database.sales import create_draft_sale, get_sales_summary
import config


async def sell_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    user_id = update.effective_user.id
    seller = get_seller_by_user_id(user_id)
    if not seller:
        await update.message.reply_text("⚠️ You are not registered as a seller.")
        return
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👆 Pick account", callback_data="sellmode:select"),
            InlineKeyboardButton("🎲 Pick any", callback_data="sellmode:any"),
        ],
    ])
    await update.message.reply_text("💰 Sell an account:", reply_markup=kb)


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
    await update.message.reply_text("💰 How would you like to bulk sell?", reply_markup=kb)


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
    summary = get_sales_summary(seller_id=seller_id)
    text = _fmt_sales_page(sales, 1, total_pages, summary=summary)
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
                f"{esc(sale_code)} | {esc(sd.get('buyer_name'))} | ₹{sd.get('price', 0):.0f}",
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
        parts.append(f"♻️ Voided: {', '.join(code(s) for s in valid)}")
    if invalid:
        parts.append(f"⚠️ Not found: {', '.join(code(i) for i in invalid)}")
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
        parts.append(f"🔴 Sold: {', '.join(code_id(i) for i in valid)}")
    if invalid:
        parts.append(f"⚠️ Not found: {', '.join(code(i) for i in invalid)}")
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
        parts.append(f"🟢 Available: {', '.join(code_id(i) for i in valid)}")
    if invalid:
        parts.append(f"⚠️ Not found: {', '.join(code(i) for i in invalid)}")
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
        parts.append(f"🟡 Pending: {', '.join(code_id(i) for i in valid)}")
    if invalid:
        parts.append(f"⚠️ Not found: {', '.join(code(i) for i in invalid)}")
    await update.message.reply_text("\n".join(parts))


def _fmt_sales_page(sales, page, total_pages, summary=None):
    text = ""
    if summary:
        s = summary
        text += (
            f"💰 <b>Revenue:</b> {config.CURRENCY}{s.get('total_revenue', 0):.0f}  "
            f"📊 <b>Sales:</b> {s.get('total_sales', 0)}  "
            f"🟡 <b>Pending:</b> {config.CURRENCY}{s.get('pending_amount', 0):.0f}\n\n"
        )
    text += f"<b>📈 Sales — page {page}/{total_pages}</b>\n\n"
    for s in sales:
        sd = _d(s)
        ps = sd.get("payment_status", "pending")
        ps_emoji = "✅" if ps == "paid" else "🟡" if ps == "pending" else "⚪"
        sale_code = sd.get("sale_code", f"#{sd.get('id', '')}")
        date = str(sd.get("sold_at", ""))[:10]
        cat = sd.get("category_name", "—")
        text += (
            f"• {code(sale_code)} | {esc(sd.get('buyer_name'))} | "
            f"{config.CURRENCY}{sd.get('price', 0):.0f} | {ps_emoji} | "
            f"{esc(cat)} | {date}\n"
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
    if args:
        await _editsale_process_ids(update, context, args[0])
        return
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏷️ By Sale ID", callback_data="editsale:mode:sale")],
        [InlineKeyboardButton("📦 By Account ID", callback_data="editsale:mode:account")],
    ])
    await update.message.reply_text(
        "✏️ What would you like to edit?\n\n"
        "🏷️ <b>Sale ID</b> — e.g. SALE-X7K9M2P4\n"
        "📦 <b>Account ID</b> — sold/pending account number",
        parse_mode="HTML",
        reply_markup=kb,
    )


async def _editsale_process_ids(update, context, raw_input):
    ids = [x.strip() for x in raw_input.split(",") if x.strip()]
    user_id = update.effective_user.id
    seller = get_seller_by_user_id(user_id)
    seller_id = seller["id"] if seller else None
    valid_sales = []
    invalid_ids = []
    created_drafts = []
    for id_str in ids:
        sale = get_sale_by_id(id_str)
        if sale:
            valid_sales.append(_d(sale))
            continue
        try:
            account_id = int(id_str)
        except ValueError:
            invalid_ids.append(id_str)
            continue
        account = get_account_by_id(account_id)
        if not account:
            invalid_ids.append(id_str)
            continue
        status = _d(account).get("status")
        if status not in ("sold", "pending_payment"):
            invalid_ids.append(id_str)
            continue
        draft_id = create_draft_sale(account_id, seller_id)
        if draft_id:
            sale = get_sale_by_id(draft_id)
            if sale:
                sd = _d(sale)
                valid_sales.append(sd)
                created_drafts.append((id_str, sd.get("sale_code", f"#{draft_id}")))
            else:
                invalid_ids.append(id_str)
        else:
            invalid_ids.append(id_str)
    if not valid_sales:
        await update.message.reply_text(f"⚠️ Not found: {', '.join(code(i) for i in invalid_ids)}")
        return
    state.set(user_id, "editsale_ids", [s["id"] for s in valid_sales])
    state.set(user_id, "editsale_pending", {})
    text = _editsale_summary(valid_sales, invalid_ids, created_drafts)
    kb = _editsale_field_keyboard()
    await update.message.reply_text(_truncate(text), parse_mode="HTML", reply_markup=kb)


def _editsale_summary(sales, invalid_ids=None, created_drafts=None):
    pending = {}
    if sales:
        user_id = None
        text = "<b>✏️ Editing sales:</b>\n\n"
        for s in sales:
            ps = s.get("payment_status", "pending")
            ps_emoji = "✅" if ps == "paid" else "🟡"
            buyer = esc(s.get("buyer_name")) or "—"
            price = s.get("price", 0) or 0
            sale_code = s.get("sale_code", f"#{s.get('id', '')}")
            text += (
                f"• {code(sale_code)} | {buyer} | "
                f"₹{price:.0f} | {ps_emoji} {esc(ps)}\n"
            )
    else:
        text = "<b>✏️ Editing sales:</b>\n\n"
    if created_drafts:
        for acct_id, sale_code in created_drafts:
            text += f"\n📝 Created {code(sale_code)} for account {code_id(acct_id)}"
    if invalid_ids:
        text += f"\n⚠️ Not found: {', '.join(code(i) for i in invalid_ids)}"
    return text


def _editsale_summary_with_pending(sales, pending, invalid_ids=None, created_drafts=None):
    text = "<b>✏️ Editing sales:</b>\n\n"
    for s in sales:
        sid = s.get("id")
        p = pending.get(sid, {})
        ps = p.get("payment_status", s.get("payment_status", "pending"))
        ps_emoji = "✅" if ps == "paid" else "🟡"
        buyer = esc(p.get("buyer_name", s.get("buyer_name"))) or "—"
        price = p.get("price", s.get("price", 0)) or 0
        sale_code = s.get("sale_code", f"#{sid}")
        text += (
            f"• {code(sale_code)} | {buyer} | "
            f"₹{price:.0f} | {ps_emoji} {esc(ps)}\n"
        )
    if created_drafts:
        for acct_id, sale_code in created_drafts:
            text += f"\n📝 Created {code(sale_code)} for account {code_id(acct_id)}"
    if invalid_ids:
        text += f"\n⚠️ Not found: {', '.join(code(i) for i in invalid_ids)}"
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
