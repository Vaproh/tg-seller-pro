from telegram import Update
from telegram.ext import ContextTypes
from core.permissions import require_seller, get_user_role
from core.format import esc
from core.help_content import HELP_MAIN_ADMIN, HELP_MAIN_SELLER, HELP_TOPICS


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not require_seller(update):
        return
    args = context.args
    role = get_user_role(update.effective_user.id)
    if not args:
        text = HELP_MAIN_ADMIN if role == "admin" else HELP_MAIN_SELLER
        await update.message.reply_text(text, parse_mode="HTML")
        return
    topic = args[0].lower().lstrip("/")
    if topic in HELP_TOPICS:
        await update.message.reply_text(HELP_TOPICS[topic], parse_mode="HTML")
    else:
        topics_list = "\n".join(f"• /help {t}" for t in sorted(HELP_TOPICS.keys()))
        await update.message.reply_text(
            f"Unknown topic: {esc(topic)}\n\nAvailable topics:\n{topics_list}",
            parse_mode="HTML",
        )
