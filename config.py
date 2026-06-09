import os
from dotenv import load_dotenv

load_dotenv()

ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

CURRENCY = "₹"
HIGH_VALUE_THRESHOLD = 500

DAILY_REPORT_HOUR = int(os.getenv("DAILY_REPORT_HOUR", "9"))
DAILY_REPORT_MINUTE = int(os.getenv("DAILY_REPORT_MINUTE", "0"))
WEEKLY_REPORT_DAY = os.getenv("WEEKLY_REPORT_DAY", "monday").lower()
TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")

MAX_USERNAME_LEN = 64
MAX_PASSWORD_LEN = 128
MAX_EMAIL_LEN = 128
MAX_NOTES_LEN = 512

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing in .env")
if not ADMIN_USER_ID:
    raise RuntimeError("ADMIN_USER_ID is missing or invalid in .env")
