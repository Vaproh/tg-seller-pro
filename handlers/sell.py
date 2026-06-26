from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.permissions import require_seller, require_admin, get_user_role
from core.state import state
from core.format import esc, code, code_id, fmt_sale_block, _d, _truncate
from core.keyboards import confirm_keyboard, sell_select_keyboard, category_keyboard
from core.filters import (
    sale_actions_keyboard,
    PAGE_SIZE,
)
from database import (
    sell_account, get_sales, count_sales,
    get_sale_by_id, void_sale, mark_payment,
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
    state.set(user_id, "sell_category", None)
    kb = category_keyboard("sellcat", include_all=True, status="available")
    if not kb:
        state.set(user_id, "sell_category", None)
        kb2 = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("👆 Pick accounts", callback_data="sellmode:selectmany"),
                InlineKeyboardButton("🔢 Enter number", callback_data="sellmode:number"),
            ],
        ])
        await update.message.reply_text("💰 Sell accounts:", reply_markup=kb2)
    else:
        await update.message.reply_text("📂 Select category to sell from:", reply_markup=kb)


async def sample_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    user_id = update.effective_user.id
    for key in ("sample_selected", "sample_page", "sample_filter",
                 "sample_stage", "sample_category"):
        state.pop(user_id, key, None)
    state.set(user_id, "sample_category", None)
    kb = category_keyboard("samplecat", include_all=True)
    if not kb:
        kb2 = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("👆 Pick accounts", callback_data="samplemode:selectmany"),
                InlineKeyboardButton("🔢 Enter number", callback_data="samplemode:number"),
            ],
        ])
        await update.message.reply_text("📋 Generate account samples:", reply_markup=kb2)
    else:
        await update.message.reply_text("📂 Select category for samples:", reply_markup=kb)


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
    sale = get_sale_by_id(args[0])
    if not sale:
        await update.message.reply_text("🔍 Sale not found.")
        return
    sd = _d(sale)
    await update.message.reply_text(
        fmt_sale_block(sale), parse_mode="HTML",
        reply_markup=sale_actions_keyboard(sd.get("id")),
    )


async def markpaid_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    seller = get_seller_by_user_id(user_id) if role != "admin" else None
    seller_id = seller["id"] if seller else None
    args = context.args
    if args:
        ids = [x.strip() for x in args[0].split(",") if x.strip()]
        results = []
        for id_str in ids:
            sale = get_sale_by_id(id_str)
            if not sale:
                results.append(f"⚠️ Not found: {code(id_str)}")
                continue
            sd = _d(sale)
            sale_code = sd.get("sale_code", f"#{sd.get('id', '')}")
            old_status = sd.get("payment_status", "pending")
            new_status = "paid" if old_status == "pending" else "pending"
            mark_payment(sd.get("id"), new_status)
            label = "paid" if new_status == "paid" else "🟡 pending"
            results.append(f"✅ {code(sale_code)} → {label}")
        await update.message.reply_text("\n".join(results), parse_mode="HTML")
        return
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
                f"{esc(sale_code)} | {config.CURRENCY}{sd.get('price', 0):.0f}",
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
        sale = get_sale_by_id(id_str)
        if not sale:
            invalid.append(id_str)
            continue
        sale_id = _d(sale).get("id")
        sale_code = _d(sale).get("sale_code", f"#{sale_id}")
        void_sale(sale_id)
        valid.append(sale_code)
    parts = []
    if valid:
        parts.append(f"♻️ Voided: {', '.join(code(s) for s in valid)}")
    if invalid:
        parts.append(f"⚠️ Not found: {', '.join(code(i) for i in invalid)}")
    if not parts:
        parts.append("⚠️ No sale IDs provided.")
    await update.message.reply_text("\n".join(parts), parse_mode="HTML")


async def marksold_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    seller = get_seller_by_user_id(user_id) if role != "admin" else None
    seller_id = seller["id"] if seller else None
    args = context.args
    if args:
        ids = [x.strip() for x in args[0].split(",") if x.strip()]
        results = []
        for id_str in ids:
            sale = get_sale_by_id(id_str)
            if not sale:
                results.append(f"⚠️ Not found: {code(id_str)}")
                continue
            sd = _d(sale)
            sale_code = sd.get("sale_code", f"#{sd.get('id', '')}")
            mark_payment(sd.get("id"), "paid")
            results.append(f"✅ {code(sale_code)} → 🔴 sold")
        await update.message.reply_text("\n".join(results), parse_mode="HTML")
        return
    pending = get_sales(limit=50, seller_id=seller_id, status="pending")
    if not pending:
        await update.message.reply_text("📭 No pending sales to mark as sold.")
        return
    buttons = []
    for s in pending:
        sd = _d(s)
        sale_code = sd.get("sale_code", f"#{sd.get('id', '')}")
        buttons.append([
            InlineKeyboardButton(
                f"{esc(sale_code)} | {config.CURRENCY}{sd.get('price', 0):.0f}",
                callback_data=f"marksold:{sd.get('id')}",
            )
        ])
    kb = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("🔴 Select a sale to mark as sold:", reply_markup=kb)


async def markunsold_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    seller = get_seller_by_user_id(user_id) if role != "admin" else None
    seller_id = seller["id"] if seller else None
    args = context.args
    if args:
        ids = [x.strip() for x in args[0].split(",") if x.strip()]
        results = []
        for id_str in ids:
            sale = get_sale_by_id(id_str)
            if not sale:
                results.append(f"⚠️ Not found: {code(id_str)}")
                continue
            sd = _d(sale)
            sale_code = sd.get("sale_code", f"#{sd.get('id', '')}")
            void_sale(sd.get("id"))
            results.append(f"✅ {code(sale_code)} → 🟢 available")
        await update.message.reply_text("\n".join(results), parse_mode="HTML")
        return
    sold = get_sales(limit=50, seller_id=seller_id, status="paid")
    if not sold:
        await update.message.reply_text("📭 No sold sales to mark as unsold.")
        return
    buttons = []
    for s in sold:
        sd = _d(s)
        sale_code = sd.get("sale_code", f"#{sd.get('id', '')}")
        buttons.append([
            InlineKeyboardButton(
                f"{esc(sale_code)} | {config.CURRENCY}{sd.get('price', 0):.0f}",
                callback_data=f"marksaleunsold:{sd.get('id')}",
            )
        ])
    kb = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("🟢 Select a sale to void (return to stock):", reply_markup=kb)


async def markpendingpayment_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    seller = get_seller_by_user_id(user_id) if role != "admin" else None
    seller_id = seller["id"] if seller else None
    args = context.args
    if args:
        ids = [x.strip() for x in args[0].split(",") if x.strip()]
        results = []
        for id_str in ids:
            sale = get_sale_by_id(id_str)
            if not sale:
                results.append(f"⚠️ Not found: {code(id_str)}")
                continue
            sd = _d(sale)
            sale_code = sd.get("sale_code", f"#{sd.get('id', '')}")
            mark_payment(sd.get("id"), "pending")
            results.append(f"✅ {code(sale_code)} → 🟡 pending payment")
        await update.message.reply_text("\n".join(results), parse_mode="HTML")
        return
    paid = get_sales(limit=50, seller_id=seller_id, status="paid")
    if not paid:
        await update.message.reply_text("📭 No paid sales to mark as pending.")
        return
    buttons = []
    for s in paid:
        sd = _d(s)
        sale_code = sd.get("sale_code", f"#{sd.get('id', '')}")
        buttons.append([
            InlineKeyboardButton(
                f"{esc(sale_code)} | {config.CURRENCY}{sd.get('price', 0):.0f}",
                callback_data=f"marksalepending:{sd.get('id')}",
            )
        ])
    kb = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("🟡 Select a sale to mark as pending payment:", reply_markup=kb)


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
        acct_id = sd.get("account_id", "")
        text += (
            f"• {code(sale_code)} | Acct {code_id(acct_id)} | "
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
        await update.message.reply_text(f"⚠️ Not found: {', '.join(code(i) for i in invalid_ids)}", parse_mode="HTML")
        return
    state.set(user_id, "editsale_ids", [s["id"] for s in valid_sales])
    state.set(user_id, "editsale_pending", {})
    text = _editsale_summary(valid_sales, invalid_ids, created_drafts)
    kb = _editsale_field_keyboard()
    await update.message.reply_text(_truncate(text), parse_mode="HTML", reply_markup=kb)


def _editsale_summary(sales, invalid_ids=None, created_drafts=None):
    if sales:
        text = "<b>✏️ Editing sales:</b>\n\n"
        for s in sales:
            ps = s.get("payment_status", "pending")
            ps_emoji = "✅" if ps == "paid" else "🟡"
            price = s.get("price", 0) or 0
            sale_code = s.get("sale_code", f"#{s.get('id', '')}")
            text += (
                f"• {code(sale_code)} | "
                f"{config.CURRENCY}{price:.0f} | {ps_emoji} {esc(ps)}\n"
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
        price = p.get("price", s.get("price", 0)) or 0
        sale_code = s.get("sale_code", f"#{sid}")
        text += (
            f"• {code(sale_code)} | "
                f"{config.CURRENCY}{price:.0f} | {ps_emoji} {esc(ps)}\n"
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
