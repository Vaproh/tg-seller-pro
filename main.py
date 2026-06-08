import os
import sys
import signal
import logging
from logging.handlers import RotatingFileHandler
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
    os.path.join(LOG_DIR, f"{config.BOT_NAME}.log"),
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

logger = logging.getLogger(config.BOT_NAME)
logger.setLevel(logging.INFO)


def shutdown(signum, frame):
    logger.info("Shutdown signal received, cleaning up...")
    try:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down.")
    except Exception as e:
        logger.error("Error shutting down scheduler: %s", e)


def main():
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    logger.info("Initializing database...")
    init_db()

    logger.info("Building application...")
    application = Application.builder().token(config.BOT_TOKEN).build()

    register_handlers(application)

    from utils.scheduler import setup_scheduler
    setup_scheduler(application)

    logger.info("Starting bot...")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
