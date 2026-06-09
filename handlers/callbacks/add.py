from telegram import Update
from telegram.ext import ContextTypes
from core.permissions import require_admin
from core.state import state
from core.format import esc, code, spoiler, code_id
from core.keyboards import add_menu_keyboard, confirm_keyboard, yes_no_keyboard, category_keyboard
from database import get_category_name
from database.accounts import add_account


async def try_handle(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str, user_id: int) -> bool:
    query = update.callback_query

    if data == "menu:add":
        if not await require_admin(update):
            return True
        await query.edit_message_text("➕ Add account:", reply_markup=add_menu_keyboard())
        return True

    if data == "menu:add:single":
        if not await require_admin(update):
            return True
        state.set(user_id, "add_stage", "username")
        await query.edit_message_text("👤 Send the Reddit username:")
        return True

    if data == "menu:add:bulk":
        if not await require_admin(update):
            return True
        kb = category_keyboard("bulkcat")
        if not kb:
            await query.edit_message_text("📂 No categories. Create one first with /addcategory")
            return True
        state.set(user_id, "bulk_stage", "category")
        await query.edit_message_text("📂 Select a category for bulk import:", reply_markup=kb)
        return True

    if data == "menu:add:csv":
        if not await require_admin(update):
            return True
        kb = category_keyboard("csvcat")
        if not kb:
            await query.edit_message_text("📂 No categories. Create one first with /addcategory")
            return True
        state.set(user_id, "csv_stage", "category")
        await query.edit_message_text("📂 Select a category for CSV import:", reply_markup=kb)
        return True

    if data.startswith("add2fa:"):
        if not await require_admin(update):
            return True
        val = data.split(":")[1] == "yes"
        state.set(user_id, "add_2fa", val)
        state.set(user_id, "add_stage", "verified")
        label = "Yes" if val else "No"
        await query.edit_message_text(
            f"✅ 2FA: {label}\nIs the account verified?",
            reply_markup=yes_no_keyboard("addverified"),
        )
        return True

    if data.startswith("addverified:"):
        if not await require_admin(update):
            return True
        val = data.split(":")[1] == "yes"
        state.set(user_id, "add_verified", val)
        state.set(user_id, "add_stage", "notes")
        label = "Yes" if val else "No"
        await query.edit_message_text(
            f"✅ Verified: {label}\nAny notes? (or /skip)"
        )
        return True

    if data.startswith("addcat:"):
        if not await require_admin(update):
            return True
        cat_id_str = data.split(":", 1)[1]
        try:
            cat_id = int(cat_id_str)
        except ValueError:
            return True
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
            f"👤 Username: {code(username)}\n"
            f"🔑 Password: {spoiler(password)}\n"
        )
        if email:
            preview += f"📧 Email: {code(email)}\n"
        if email_password:
            preview += f"🔑 Email Pass: {spoiler(email_password)}\n"
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
        return True

    if data == "addconfirm":
        if not await require_admin(update):
            return True
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
            return True
        success, msg, acc_id = add_account(
            username, password, cat_id,
            email=email, email_password=email_password,
            has_2fa=has_2fa, is_verified=is_verified, notes=notes,
        )
        if success:
            await query.edit_message_text(f"✅ Account saved! (ID: #{code_id(acc_id)})")
        else:
            await query.edit_message_text(f"❌ {msg}")
        return True

    if data == "addcancel":
        if not await require_admin(update):
            return True
        for key in ("add_username", "add_password", "add_email", "add_email_password",
                     "add_2fa", "add_verified", "add_notes", "add_category_id", "add_stage"):
            state.pop(user_id, key, None)
        await query.edit_message_text("❌ Account add cancelled.")
        return True

    return False
