import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.permissions import require_seller, require_admin
from core.state import state
from core.format import esc
from core.keyboards import category_keyboard, confirm_keyboard, sell_accounts_keyboard, yes_no_keyboard
from database import (
    add_account, add_accounts_bulk, get_account_by_id,
    list_accounts, sell_account, get_category_name,
)
from utils.parsers import parse_bulk_lines, parse_csv_file
from utils.csv_utils import detect_columns, build_accounts_from_csv
from utils.notifications import notify_admin, fmt_bulk_import
import config

logger = logging.getLogger(__name__)

MAX_CSV_SIZE = 5 * 1024 * 1024


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    user_id = update.effective_user.id
    text = update.message.text.strip()

    stage = state.get(user_id, "add_stage")
    if stage == "username":
        if len(text) > config.MAX_USERNAME_LEN:
            await update.message.reply_text(f"⚠️ Username too long (max {config.MAX_USERNAME_LEN} chars).")
            return
        state.set(user_id, "add_username", text)
        state.set(user_id, "add_stage", "password")
        await update.message.reply_text(f"✅ Username: {esc(text)}\n🔑 Send the password:")
        return

    if stage == "password":
        if len(text) > config.MAX_PASSWORD_LEN:
            await update.message.reply_text(f"⚠️ Password too long (max {config.MAX_PASSWORD_LEN} chars).")
            return
        state.set(user_id, "add_password", text)
        state.set(user_id, "add_stage", "email")
        await update.message.reply_text("✅ Password saved\n📧 Send email (or /skip):")
        return

    if stage == "email":
        if text.lower() == "/skip":
            state.set(user_id, "add_email", None)
            state.set(user_id, "add_stage", "email_password")
            await update.message.reply_text("📧 Send email password (or /skip):")
            return
        if len(text) > config.MAX_EMAIL_LEN:
            await update.message.reply_text(f"⚠️ Email too long (max {config.MAX_EMAIL_LEN} chars).")
            return
        state.set(user_id, "add_email", text)
        state.set(user_id, "add_stage", "email_password")
        await update.message.reply_text(f"✅ Email: {esc(text)}\n📧 Send email password (or /skip):")
        return

    if stage == "email_password":
        if text.lower() == "/skip":
            state.set(user_id, "add_email_password", None)
            state.set(user_id, "add_stage", "2fa")
            await update.message.reply_text("🔐 Is 2FA enabled?", reply_markup=yes_no_keyboard("add2fa"))
            return
        state.set(user_id, "add_email_password", text)
        state.set(user_id, "add_stage", "2fa")
        await update.message.reply_text("✅ Email password saved\n🔐 Is 2FA enabled?", reply_markup=yes_no_keyboard("add2fa"))
        return

    if stage == "notes":
        if text.lower() == "/skip":
            state.set(user_id, "add_notes", None)
            state.set(user_id, "add_stage", "category")
            kb = category_keyboard("addcat")
            if kb:
                await update.message.reply_text("📂 Select category:", reply_markup=kb)
            else:
                await update.message.reply_text("📂 No categories. Create one with /addcategory first.")
            return
        if len(text) > config.MAX_NOTES_LEN:
            await update.message.reply_text(f"⚠️ Notes too long (max {config.MAX_NOTES_LEN} chars).")
            return
        state.set(user_id, "add_notes", text)
        state.set(user_id, "add_stage", "category")
        kb = category_keyboard("addcat")
        if kb:
            await update.message.reply_text("✅ Notes saved\n📂 Select category:", reply_markup=kb)
        else:
            await update.message.reply_text("📂 No categories. Create one with /addcategory first.")
        return

    bulk_stage = state.get(user_id, "bulk_stage")
    if bulk_stage == "lines":
        if text.lower() == "/done":
            raw = state.get(user_id, "bulk_lines", "")
            cat_id = state.get(user_id, "bulk_category")
            items = parse_bulk_lines(raw)
            if not items:
                await update.message.reply_text("📭 No valid lines found.")
                state.pop(user_id, "bulk_stage")
                state.pop(user_id, "bulk_lines")
                state.pop(user_id, "bulk_category")
                return
            result = add_accounts_bulk(items, cat_id)
            cat_name = get_category_name(cat_id) or "—"
            state.pop(user_id, "bulk_stage")
            state.pop(user_id, "bulk_lines")
            state.pop(user_id, "bulk_category")
            msg = f"📥 Bulk import: {result['added']} added, {result['skipped']} skipped in {cat_name}"
            await update.message.reply_text(msg)
            await notify_admin(context, fmt_bulk_import(result["added"], result["skipped"], cat_name))
            return
        current = state.get(user_id, "bulk_lines", "")
        if len(current) > 100000:
            await update.message.reply_text("⚠️ Bulk input too large. Send /done to process what you have.")
            return
        state.set(user_id, "bulk_lines", current + text + "\n")
        lines = text.strip().splitlines()
        await update.message.reply_text(f"✅ {len(lines)} lines received. Send more or /done.")
        return

    bd_mode = state.get(user_id, "bulk_delete_mode")
    if bd_mode == "input":
        state.set(user_id, "bulk_delete_input", text)
        state.set(user_id, "bulk_delete_mode", "confirm")
        await update.message.reply_text(
            f"⚠️ Confirm delete:\n<code>{esc(text)}</code>",
            parse_mode="HTML",
            reply_markup=confirm_keyboard("bulkdelconfirm", "bulkdelcancel"),
        )
        return

    preview_stage = state.get(user_id, "preview_stage")
    if preview_stage == "count":
        from handlers.preview import handle_preview_count
        await handle_preview_count(update, context, text)
        return

    search_stage = state.get(user_id, "search_stage")
    if search_stage == "value":
        from handlers.search import handle_search_value
        await handle_search_value(update, context, text)
        return

    sell_stage = state.get(user_id, "sell_stage")
    if sell_stage == "buyer":
        if len(text) > config.MAX_BUYER_LEN:
            await update.message.reply_text(f"⚠️ Buyer name too long (max {config.MAX_BUYER_LEN} chars).")
            return
        state.set(user_id, "sell_buyer", text)
        account_id = state.get(user_id, "sell_account_id")
        account = get_account_by_id(account_id)
        default_price = 0
        if account:
            from database.categories import list_categories as lc
            cats = lc()
            for c in cats:
                if c["id"] == account["category_id"]:
                    default_price = c["default_price"]
                    break
        state.set(user_id, "sell_stage", "price")
        await update.message.reply_text(
            f"👤 Buyer: {esc(text)}\n"
            f"💰 Default price: ₹{default_price:.0f}\n💸 Enter price (or /skip for default):"
        )
        return

    if sell_stage == "price":
        if text.lower() == "/skip":
            account_id = state.get(user_id, "sell_account_id")
            account = get_account_by_id(account_id)
            default_price = 0
            if account:
                from database.categories import list_categories as lc
                cats = lc()
                for c in cats:
                    if c["id"] == account["category_id"]:
                        default_price = c["default_price"]
                        break
            price = default_price
        else:
            try:
                price = float(text.replace("₹", "").replace(",", ""))
            except ValueError:
                await update.message.reply_text("⚠️ Enter a valid price:")
                return
            if price < 0:
                await update.message.reply_text("⚠️ Price must be positive:")
                return
        state.set(user_id, "sell_price", price)
        state.set(user_id, "sell_stage", "tags")
        await update.message.reply_text("🏷️ Add tags? (or /skip)")
        return

    if sell_stage == "tags":
        tags = text if text.lower() != "/skip" else None
        state.set(user_id, "sell_tags", tags)
        account_id = state.get(user_id, "sell_account_id")
        buyer = state.get(user_id, "sell_buyer")
        price = state.get(user_id, "sell_price")
        account = get_account_by_id(account_id)
        if not account:
            await update.message.reply_text("🔍 Account not found.")
            state.pop(user_id, "sell_stage")
            return
        text_preview = (
            f"<b>Confirm Sale:</b>\n\n"
            f"Account: #{account['id']} — {esc(account['username'])}\n"
            f"Buyer: {esc(buyer)}\n"
            f"Price: ₹{price:.0f}\n"
            f"Tags: {esc(tags) if tags else '—'}\n\n"
            f"✅ Confirm?"
        )
        state.set(user_id, "sell_stage", "confirm")
        await update.message.reply_text(
            text_preview,
            parse_mode="HTML",
            reply_markup=confirm_keyboard("sellconfirm", "sellcancel"),
        )
        return

    bulksell_stage = state.get(user_id, "bulksell_stage")
    if bulksell_stage == "buyer":
        if len(text) > config.MAX_BUYER_LEN:
            await update.message.reply_text(f"⚠️ Buyer name too long (max {config.MAX_BUYER_LEN} chars).")
            return
        state.set(user_id, "bulksell_buyer", text)
        state.set(user_id, "bulksell_stage", "price")
        await update.message.reply_text("💰 Enter price per account:")
        return

    if bulksell_stage == "price":
        try:
            price = float(text.replace("₹", "").replace(",", ""))
        except ValueError:
                await update.message.reply_text("⚠️ Enter a valid price:")
            return
        if price < 0:
            await update.message.reply_text("⚠️ Price must be positive:")
            return
        state.set(user_id, "bulksell_price", price)
        state.set(user_id, "bulksell_stage", "select")
        accounts = list_accounts(limit=20, status="active")
        if not accounts:
            await update.message.reply_text("📭 No available accounts.")
            state.pop(user_id, "bulksell_stage")
            return
        kb = sell_accounts_keyboard(accounts, "bulksellselect")
        await update.message.reply_text("💰 Select accounts to sell:", reply_markup=kb)
        return


async def handle_csv_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    user_id = update.effective_user.id
    csv_stage = state.get(user_id, "csv_stage")
    if csv_stage != "upload":
        return
    doc = update.message.document
    if not doc or not doc.file_name.lower().endswith(".csv"):
        await update.message.reply_text("📁 Please upload a CSV file.")
        return
    if doc.file_size and doc.file_size > MAX_CSV_SIZE:
        await update.message.reply_text(f"⚠️ CSV file too large (max {MAX_CSV_SIZE // (1024*1024)}MB).")
        return
    file = await doc.get_file()
    content = await file.download_as_bytearray()
    headers, data = parse_csv_file(bytes(content))
    if not headers:
        await update.message.reply_text("⚠️ Could not parse CSV.")
        return
    state.set(user_id, "csv_headers", headers)
    state.set(user_id, "csv_data", data)
    state.set(user_id, "csv_mapping", {})
    state.set(user_id, "csv_stage", "map_username")
    buttons = [[InlineKeyboardButton(h, callback_data=f"csvcol:{i}")] for i, h in enumerate(headers)]
    await update.message.reply_text(
        f"<b>CSV Columns Detected:</b> {', '.join(headers)}\n\n"
        "Which column is the <b>Reddit username</b>?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
