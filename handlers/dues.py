from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.permissions import require_seller, require_admin, get_user_role
from core.format import esc, code, _truncate
from core.state import state
from database.sellers import get_seller_by_user_id, list_sellers
from database.dues import (
    add_due, remove_due, get_dues_balance,
    get_all_dues_balances, get_dues_history, count_dues,
)
import config

DUES_PER_PAGE = 5


def _fmt_due_entry(entry):
    e = dict(entry) if not isinstance(entry, dict) else entry
    due_type = e.get("type", "add")
    amount = e.get("amount", 0)
    reason = e.get("reason") or "—"
    seller_name = e.get("seller_name", "—")
    created_at = e.get("created_at", "?")
    emoji = "📈" if due_type == "add" else "📉"
    sign = "+" if due_type == "add" else "-"
    return (
        f"{emoji} <b>{esc(seller_name)}</b>\n"
        f"💰 {sign}{config.CURRENCY}{amount:.0f}\n"
        f"📝 {esc(reason)}\n"
        f"🕒 <code>{esc(str(created_at)[:19])}</code>"
    )


def _fmt_dues_page(entries, page, total_pages, summary_text=""):
    text = f"<b>💳 Dues — page {page}/{total_pages}</b>\n"
    if summary_text:
        text += f"{summary_text}\n"
    text += "\n"
    for entry in entries:
        text += _fmt_due_entry(entry) + "\n\n"
    if not entries:
        text += "📭 No dues found."
    return text


def _dues_keyboard(page, total_pages):
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"duespage:{page - 1}"))
    nav_row.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("➡️", callback_data=f"duespage:{page + 1}"))
    return InlineKeyboardMarkup([nav_row])


async def dues_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    seller = get_seller_by_user_id(user_id)
    if role != "admin" and not seller:
        await update.message.reply_text("⚠️ You are not registered as a seller.")
        return
    args = context.args
    if args and args[0].lower() == "all" and role == "admin":
        balances = get_all_dues_balances()
        if not balances:
            await update.message.reply_text("📭 No pending dues.")
            return
        text = "<b>💳 All Seller Dues</b>\n\n"
        for b in balances:
            bd = dict(b) if not isinstance(b, dict) else b
            text += f"👤 <code>{esc(bd['seller_name'])}</code> — {config.CURRENCY}{bd['balance']:.0f}\n"
        await update.message.reply_text(_truncate(text), parse_mode="HTML")
        return
    if args and role == "admin":
        target_name = args[0].lstrip("@")
        sellers = list_sellers()
        target = None
        for s in sellers:
            sd = dict(s) if not isinstance(s, dict) else s
            if sd["name"].lower() == target_name.lower():
                target = sd
                break
        if not target:
            await update.message.reply_text(f"⚠️ Seller <code>{esc(target_name)}</code> not found.", parse_mode="HTML")
            return
        balance = get_dues_balance(target["id"])
        total = count_dues(seller_id=target["id"])
        total_pages = max(1, (total + DUES_PER_PAGE - 1) // DUES_PER_PAGE)
        entries = get_dues_history(seller_id=target["id"], limit=DUES_PER_PAGE, offset=0)
        summary = f"\n👤 <b>{esc(target['name'])}</b> — Total: {config.CURRENCY}{balance:.0f}"
        text = _fmt_dues_page(entries, 1, total_pages, summary)
        kb = _dues_keyboard(1, total_pages)
        context.user_data["dues_seller_id"] = target["id"]
        await update.message.reply_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return
    seller_id = seller["id"] if seller else None
    if role == "admin":
        balances = get_all_dues_balances()
        text = "<b>💳 Seller Dues Overview</b>\n\n"
        if balances:
            for b in balances:
                bd = dict(b) if not isinstance(b, dict) else b
                text += f"👤 <code>{esc(bd['seller_name'])}</code> — {config.CURRENCY}{bd['balance']:.0f}\n"
        else:
            text += "📭 No pending dues."
        text += "\n\n<i>Use /dues @name for seller history</i>"
        await update.message.reply_text(_truncate(text), parse_mode="HTML")
        return
    balance = get_dues_balance(seller_id) if seller_id else 0
    total = count_dues(seller_id=seller_id)
    if total == 0:
        await update.message.reply_text(
            f"💳 <b>Your Dues:</b> {config.CURRENCY}{balance:.0f}\n\n📭 No dues history.",
            parse_mode="HTML",
        )
        return
    total_pages = max(1, (total + DUES_PER_PAGE - 1) // DUES_PER_PAGE)
    entries = get_dues_history(seller_id=seller_id, limit=DUES_PER_PAGE, offset=0)
    summary = f"\n💰 <b>Total Due:</b> {config.CURRENCY}{balance:.0f}"
    text = _fmt_dues_page(entries, 1, total_pages, summary)
    kb = _dues_keyboard(1, total_pages)
    context.user_data["dues_seller_id"] = seller_id
    await update.message.reply_text(_truncate(text), parse_mode="HTML", reply_markup=kb)


async def duesadd_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    user_id = update.effective_user.id
    seller = get_seller_by_user_id(user_id)
    if not seller:
        await update.message.reply_text("⚠️ You are not registered as a seller.")
        return
    args = context.args
    if args:
        try:
            amount = float(args[0])
            if amount <= 0:
                await update.message.reply_text("⚠️ Amount must be positive.")
                return
        except ValueError:
            await update.message.reply_text("⚠️ Invalid amount. Usage: /duesadd 500")
            return
        reason = " ".join(args[1:]) if len(args) > 1 else None
        if not reason:
            state.set(user_id, "duesadd_amount", amount)
            state.set(user_id, "duesadd_step", "reason")
            await update.message.reply_text(
                f"💰 Adding {config.CURRENCY}{amount:.0f} to dues.\n\n"
                f"📝 Please enter a reason for this due:"
            )
            return
        add_due(seller["id"], amount, reason)
        await update.message.reply_text(
            f"✅ <b>Due Added</b>\n\n"
            f"💰 Amount: {config.CURRENCY}{amount:.0f}\n"
            f"📝 Reason: {esc(reason)}",
            parse_mode="HTML",
        )
        return
    state.set(user_id, "duesadd_step", "amount")
    await update.message.reply_text(
        "💰 <b>Add Due</b>\n\nHow much do you want to add?",
        parse_mode="HTML",
    )


async def duesremove_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    user_id = update.effective_user.id
    seller = get_seller_by_user_id(user_id)
    if not seller:
        await update.message.reply_text("⚠️ You are not registered as a seller.")
        return
    args = context.args
    if args:
        try:
            amount = float(args[0])
            if amount <= 0:
                await update.message.reply_text("⚠️ Amount must be positive.")
                return
        except ValueError:
            await update.message.reply_text("⚠️ Invalid amount. Usage: /duesremove 500")
            return
        balance = get_dues_balance(seller["id"])
        if amount > balance:
            await update.message.reply_text(
                f"⚠️ Cannot remove {config.CURRENCY}{amount:.0f}. "
                f"Your balance is {config.CURRENCY}{balance:.0f}."
            )
            return
        reason = " ".join(args[1:]) if len(args) > 1 else None
        if not reason:
            state.set(user_id, "duesremove_amount", amount)
            state.set(user_id, "duesremove_step", "reason")
            await update.message.reply_text(
                f"📉 Removing {config.CURRENCY}{amount:.0f} from dues.\n\n"
                f"📝 Please enter a reason for this removal:"
            )
            return
        remove_due(seller["id"], amount, reason)
        await update.message.reply_text(
            f"✅ <b>Due Removed</b>\n\n"
            f"💰 Amount: {config.CURRENCY}{amount:.0f}\n"
            f"📝 Reason: {esc(reason)}",
            parse_mode="HTML",
        )
        return
    balance = get_dues_balance(seller["id"])
    if balance <= 0:
        await update.message.reply_text("📭 No dues to remove.")
        return
    state.set(user_id, "duesremove_step", "amount")
    await update.message.reply_text(
        f"📉 <b>Remove Due</b> (Balance: {config.CURRENCY}{balance:.0f})\n\nHow much do you want to remove?",
        parse_mode="HTML",
    )
