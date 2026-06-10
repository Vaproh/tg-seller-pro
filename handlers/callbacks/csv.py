from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.permissions import require_admin
from core.state import state
from core.format import esc, code, spoiler, _truncate
from core.keyboards import confirm_keyboard, category_keyboard
from database import get_category_name, add_accounts_bulk
from utils.csv_utils import build_accounts_from_csv
from utils.notifications import notify_admin


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
        text += f"• {code(acc.get('username', ''))} | {spoiler(str(acc.get('password', ''))[:4])}***"
        if acc.get("email"):
            text += f" | {esc(acc['email'])}"
        text += "\n"
    if len(accounts) > 3:
        text += f"\n... and {len(accounts) - 3} more"
    await query.edit_message_text(
        text, parse_mode="HTML",
        reply_markup=confirm_keyboard("csvconfirm", "csvcancel"),
    )


async def try_handle(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str, user_id: int) -> bool:
    query = update.callback_query
    await query.answer()

    if data.startswith("csvcat:"):
        cat_id_str = data.split(":", 1)[1]
        try:
            cat_id = int(cat_id_str)
        except ValueError:
            return True
        state.set(user_id, "csv_category", cat_id)
        state.set(user_id, "csv_stage", "upload")
        await query.edit_message_text("📁 Upload a CSV file:")
        return True

    if data.startswith("csvcol:"):
        if not await require_admin(update):
            return True
        try:
            col_idx = int(data.split(":")[1])
        except (ValueError, IndexError):
            return True
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
        return True

    if data.startswith("csvbool:"):
        if not await require_admin(update):
            return True
        parts = data.split(":")
        field = parts[1]
        val = parts[2] == "yes"
        db_key = "has_2fa" if field == "2fa" else "is_verified" if field == "verified" else field
        mapping = state.get(user_id, "csv_mapping", {})
        mapping[db_key] = val
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
        return True

    if data.startswith("csvskip:"):
        if not await require_admin(update):
            return True
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
        return True

    if data == "csvconfirm":
        if not await require_admin(update):
            return True
        headers = state.pop(user_id, "csv_headers")
        csv_data = state.pop(user_id, "csv_data")
        mapping = state.pop(user_id, "csv_mapping")
        cat_id = state.pop(user_id, "csv_category")
        state.pop(user_id, "csv_stage", None)
        if not headers or not csv_data or not mapping:
            await query.edit_message_text("❌ CSV import data lost. Try again.")
            return True
        accounts = build_accounts_from_csv(headers, csv_data, mapping)
        if not accounts:
            await query.edit_message_text("📭 No valid accounts found in CSV.")
            return True
        result = add_accounts_bulk(accounts, cat_id)
        cat_name = get_category_name(cat_id) or "—"
        msg = f"📥 CSV import: {result['added']} added, {result['skipped']} skipped in {cat_name}"
        await query.edit_message_text(msg)
        await notify_admin(context, f"📥 CSV import: {result['added']} added, {result['skipped']} skipped in {cat_name}")
        return True

    if data == "csvcancel":
        for key in ("csv_headers", "csv_data", "csv_mapping", "csv_category", "csv_stage"):
            state.pop(user_id, key, None)
        await query.edit_message_text("❌ CSV import cancelled.")
        return True

    return False
