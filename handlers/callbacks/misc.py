import os
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from core.permissions import require_seller, require_admin, get_user_role
from core.state import state
from core.format import esc, code, _truncate
from core.keyboards import settings_keyboard, report_period_keyboard, category_keyboard
from database import get_category_name
from handlers.preview import handle_preview_category
import config
from handlers.reports import handle_report_period


async def try_handle(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str, user_id: int) -> bool:
    query = update.callback_query
    await query.answer()

    if data == "noop":
        return True

    if data == "menu:preview":
        kb = category_keyboard("previewcat", include_all=True)
        if not kb:
            await query.edit_message_text("📭 No categories found.")
            return True
        await query.edit_message_text("📂 Select a category:", reply_markup=kb)
        return True

    if data.startswith("previewcat:"):
        cat_id_str = data.split(":", 1)[1]
        await handle_preview_category(update, context, cat_id_str)
        return True

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
        return True

    if data == "menu:sellers":
        if not await require_admin(update):
            return True
        from database import list_sellers
        sellers = list_sellers()
        if not sellers:
            await query.edit_message_text("📭 No sellers registered.")
            return True
        text = "<b>👥 Sellers</b>\n\n"
        for s in sellers:
            status = "🟢" if s["active"] else "🔴"
            text += (
                f"{status} {esc(s['name'])} (ID: {code(s['user_id'])}) — "
                f"{s['sale_count']} sales, {config.CURRENCY}{s['total_earnings']:.0f}\n"
            )
        await query.edit_message_text(text, parse_mode="HTML")
        return True

    if data == "menu:report":
        if not await require_admin(update):
            return True
        await query.edit_message_text("📊 Select a period:", reply_markup=report_period_keyboard())
        return True

    if data.startswith("report:"):
        if not await require_admin(update):
            return True
        period = data.split(":", 1)[1]
        await handle_report_period(update, context, period)
        return True

    if data == "menu:settings":
        if not await require_admin(update):
            return True
        await query.edit_message_text("⚙️ Settings:", reply_markup=settings_keyboard())
        return True

    if data == "menu:export":
        if not await require_admin(update):
            return True
        from database import export_accounts_csv
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
        return True

    if data == "menu:backup":
        if not await require_admin(update):
            return True
        from database.connection import DB_PATH
        if not os.path.exists(DB_PATH):
            await context.bot.send_message(chat_id=user_id, text="📭 No database found.")
            return True
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
        return True

    if data.startswith("bulkcat:"):
        cat_id_str = data.split(":", 1)[1]
        if cat_id_str == "all":
            return True
        try:
            cat_id = int(cat_id_str)
        except ValueError:
            return True
        cat_name = get_category_name(cat_id)
        if not cat_name:
            await query.edit_message_text("🔍 Category not found.")
            return True
        state.set(user_id, "bulk_category", cat_id)
        state.set(user_id, "bulk_stage", "lines")
        await query.edit_message_text(
            f"Category: {cat_name}\n\n"
            "Send accounts in format:\n<code>user:pass</code>\n"
            "One per line. Send /done when finished.",
            parse_mode="HTML",
        )
        return True

    if data.startswith("help:"):
        if not await require_seller(update):
            return True
        topic = data.split(":", 1)[1]
        from handlers.help import handle_help_callback
        await handle_help_callback(update, context, topic)
        return True

    return False
