import os
import shutil
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from core.permissions import require_admin
from database import export_accounts_csv


async def export_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not require_admin(update):
        return
    csv_data = export_accounts_csv()
    filename = f"accounts_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join("/tmp", filename)
    try:
        with open(filepath, "wb") as f:
            f.write(csv_data)
        with open(filepath, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=filename,
                caption="📤 Accounts export",
            )
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


async def backup_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not require_admin(update):
        return
    from database.connection import DB_PATH
    if not os.path.exists(DB_PATH):
        await update.message.reply_text("No database found.")
        return
    filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    filepath = os.path.join("/tmp", filename)
    try:
        shutil.copy2(DB_PATH, filepath)
        with open(filepath, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=filename,
                caption="💾 Database backup",
            )
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)
