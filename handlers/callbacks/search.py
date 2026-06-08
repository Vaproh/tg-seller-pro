from telegram import Update
from telegram.ext import ContextTypes
from core.permissions import require_seller
from handlers.search import handle_search_type, handle_search_category, handle_search_status


async def try_handle(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str, user_id: int) -> bool:

    if data.startswith("search:"):
        if not await require_seller(update):
            return True
        search_type = data.split(":", 1)[1]
        await handle_search_type(update, context, search_type)
        return True

    if data.startswith("searchcat:"):
        if not await require_seller(update):
            return True
        cat_id_str = data.split(":", 1)[1]
        await handle_search_category(update, context, cat_id_str)
        return True

    if data.startswith("searchstatus:"):
        if not await require_seller(update):
            return True
        status_val = data.split(":", 1)[1]
        await handle_search_status(update, context, status_val)
        return True

    return False
