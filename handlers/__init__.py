import logging
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters,
)
from handlers.start import start, mainmenu, ping
from handlers.accounts import (
    add_cmd, add_bulk_cmd, getid_cmd, delete_cmd,
    bulkdelete_cmd, extractcsv_cmd, list_cmd,
)
from handlers.sell import (
    sell_cmd, bulksell_cmd, sales_cmd, sale_cmd,
    markpaid_cmd, voidsale_cmd,
    marksold_cmd, markunsold_cmd, markpendingpayment_cmd,
    editsale_cmd,
)
from handlers.preview import preview_cmd
from handlers.search import search_cmd
from handlers.categories import categories_cmd, addcategory_cmd, deletecategory_cmd
from handlers.inventory import inventory_cmd
from handlers.buyers import buyers_cmd, buyer_cmd
from handlers.reports import report_cmd
from handlers.sellers import addseller_cmd, removeseller_cmd, listsellers_cmd
from handlers.export import export_cmd, backup_cmd
from handlers.callbacks import handle_callback
from handlers.messages import handle_text, handle_csv_upload
from handlers.errors import error_handler
from handlers.help import help_command
from handlers.command_logger import log_command

logger = logging.getLogger(__name__)


def register_handlers(application: Application):
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("mainmenu", mainmenu))
    application.add_handler(CommandHandler("ping", ping))
    application.add_handler(CommandHandler("help", help_command))

    application.add_handler(CommandHandler("add", add_cmd))
    application.add_handler(CommandHandler("bulkadd", add_bulk_cmd))
    application.add_handler(CommandHandler("getid", getid_cmd))
    application.add_handler(CommandHandler("delete", delete_cmd))
    application.add_handler(CommandHandler("bulkdelete", bulkdelete_cmd))
    application.add_handler(CommandHandler("extractcsv", extractcsv_cmd))
    application.add_handler(CommandHandler("list", list_cmd))

    application.add_handler(CommandHandler("sell", sell_cmd))
    application.add_handler(CommandHandler("bulksell", bulksell_cmd))
    application.add_handler(CommandHandler("sales", sales_cmd))
    application.add_handler(CommandHandler("sale", sale_cmd))
    application.add_handler(CommandHandler("markpaid", markpaid_cmd))
    application.add_handler(CommandHandler("voidsale", voidsale_cmd))
    application.add_handler(CommandHandler("marksold", marksold_cmd))
    application.add_handler(CommandHandler("markunsold", markunsold_cmd))
    application.add_handler(CommandHandler("markpendingpayment", markpendingpayment_cmd))
    application.add_handler(CommandHandler("editsale", editsale_cmd))

    application.add_handler(CommandHandler("preview", preview_cmd))
    application.add_handler(CommandHandler("search", search_cmd))

    application.add_handler(CommandHandler("categories", categories_cmd))
    application.add_handler(CommandHandler("addcategory", addcategory_cmd))
    application.add_handler(CommandHandler("deletecategory", deletecategory_cmd))

    application.add_handler(CommandHandler("inventory", inventory_cmd))

    application.add_handler(CommandHandler("buyers", buyers_cmd))
    application.add_handler(CommandHandler("buyer", buyer_cmd))

    application.add_handler(CommandHandler("report", report_cmd))

    application.add_handler(CommandHandler("addseller", addseller_cmd))
    application.add_handler(CommandHandler("removeseller", removeseller_cmd))
    application.add_handler(CommandHandler("listsellers", listsellers_cmd))

    application.add_handler(CommandHandler("export", export_cmd))
    application.add_handler(CommandHandler("backup", backup_cmd))

    application.add_handler(CallbackQueryHandler(handle_callback))

    application.add_handler(MessageHandler(filters.Document.ALL, handle_csv_upload))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    application.add_error_handler(error_handler)

    application.add_handler(
        MessageHandler(filters.COMMAND, log_command), group=-1
    )

    logger.info("All handlers registered.")
