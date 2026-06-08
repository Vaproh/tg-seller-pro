import os
import sys
import signal
import logging
from logging.handlers import RotatingFileHandler
from telegram import BotCommand
from telegram.ext import Application
import config
from database import init_db
from handlers import register_handlers
from utils.scheduler import scheduler

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

root_logger = logging.getLogger()
root_logger.setLevel(logging.WARNING)

file_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, "reddit-seller-bot.log"),
    maxBytes=5 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
root_logger.addHandler(file_handler)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
root_logger.addHandler(console_handler)

for name in ("telegram", "urllib3", "asyncio"):
    logging.getLogger(name).setLevel(logging.WARNING)

logger = logging.getLogger("reddit-seller-bot")
logger.setLevel(logging.INFO)


def shutdown(signum, frame):
    logger.info("Shutdown signal received, cleaning up...")
    try:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down.")
    except Exception as e:
        logger.error("Error shutting down scheduler: %s", e)


async def post_init(application):
    from utils.scheduler import setup_scheduler
    setup_scheduler(application)
    logger.info("Scheduler started.")

    commands = [
        BotCommand("start", "🚀 Start the bot"),
        BotCommand("help", "📖 Show help"),
        BotCommand("mainmenu", "📋 Main menu"),
        BotCommand("ping", "🏓 Health check"),
        BotCommand("add", "➕ Add single account (admin)"),
        BotCommand("bulkadd", "📥 Bulk import (admin)"),
        BotCommand("extractcsv", "📄 CSV import (admin)"),
        BotCommand("list", "📋 Browse accounts"),
        BotCommand("search", "🔎 Search accounts"),
        BotCommand("getid", "🔍 View account by ID"),
        BotCommand("sell", "💰 Sell an account"),
        BotCommand("bulksell", "💰 Bulk sell accounts"),
        BotCommand("sales", "📈 View all sales"),
        BotCommand("sale", "🧾 Sale detail by ID"),
        BotCommand("markpaid", "💳 Toggle payment status"),
        BotCommand("voidsale", "♻️ Void a sale (admin)"),
        BotCommand("marksold", "🔴 Mark account sold"),
        BotCommand("markunsold", "🟢 Mark account available"),
        BotCommand("markpendingpayment", "🟡 Mark pending payment"),
        BotCommand("preview", "📂 Preview for buyer"),
        BotCommand("categories", "📂 List categories"),
        BotCommand("addcategory", "➕ Create category (admin)"),
        BotCommand("deletecategory", "🗑️ Delete category (admin)"),
        BotCommand("inventory", "📦 Stock overview"),
        BotCommand("buyers", "👥 List buyers"),
        BotCommand("buyer", "👤 Buyer history"),
        BotCommand("report", "📊 Revenue reports (admin)"),
        BotCommand("addseller", "👤 Register seller (admin)"),
        BotCommand("removeseller", "🚫 Remove seller (admin)"),
        BotCommand("listsellers", "👥 List sellers (admin)"),
        BotCommand("export", "📤 Export CSV (admin)"),
        BotCommand("backup", "💾 DB backup (admin)"),
        BotCommand("delete", "🗑️ Delete account (admin)"),
        BotCommand("bulkdelete", "🗑️ Bulk delete (admin)"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands registered with Telegram.")


def main():
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    logger.info("Initializing database...")
    init_db()

    logger.info("Building application...")
    application = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    register_handlers(application)

    logger.info("Starting bot...")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
