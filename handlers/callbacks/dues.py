import logging
from telegram import Update
from telegram.ext import ContextTypes
from core.state import state
from core.format import esc, _truncate
from database.dues import get_dues_history, count_dues

logger = logging.getLogger(__name__)

DUES_PER_PAGE = 5


async def handle_dues_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str, user_id: int) -> bool:
    query = update.callback_query

    if data.startswith("duespage:"):
        await query.answer()
        try:
            page = int(data.split(":")[1])
        except (IndexError, ValueError):
            return True
        seller_id = context.user_data.get("dues_seller_id")
        total = count_dues(seller_id=seller_id)
        total_pages = max(1, (total + DUES_PER_PAGE - 1) // DUES_PER_PAGE)
        if page < 1 or page > total_pages:
            return True
        offset = (page - 1) * DUES_PER_PAGE
        entries = get_dues_history(seller_id=seller_id, limit=DUES_PER_PAGE, offset=offset)
        from handlers.dues import _fmt_dues_page, _dues_keyboard
        text = _fmt_dues_page(entries, page, total_pages)
        kb = _dues_keyboard(page, total_pages)
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return True

    return False
