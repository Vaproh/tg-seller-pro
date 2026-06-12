from telegram import Update
from telegram.ext import ContextTypes

from handlers.callbacks.menu import try_handle as handle_menu
from handlers.callbacks.add import try_handle as handle_add
from handlers.callbacks.sell import try_handle as handle_sell
from handlers.callbacks.list import try_handle as handle_list
from handlers.callbacks.sales import try_handle as handle_sales
from handlers.callbacks.csv import try_handle as handle_csv
from handlers.callbacks.search import try_handle as handle_search
from handlers.callbacks.misc import try_handle as handle_misc
from handlers.callbacks.transfersales import handle_transfersales_callback
from handlers.stats import stats_callback


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    for handler in (
        handle_misc,
        handle_menu,
        handle_add,
        handle_sell,
        handle_list,
        handle_sales,
        handle_csv,
        handle_search,
    ):
        if await handler(update, context, data, user_id):
            return

    if await stats_callback(update, context, data, user_id):
        return

    if await handle_transfersales_callback(update, context, data, user_id):
        return
