from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.permissions import require_seller, get_user_role
from core.format import esc
from core.help_content import HELP_MAIN_ADMIN, HELP_MAIN_SELLER, HELP_TOPICS


TOPIC_EMOJIS = {
    "sell": "💰",
    "preview": "📂",
    "accounts": "➕",
    "search": "🔎",
    "categories": "📂",
    "sales": "📈",
    "buyers": "👥",
    "inventory": "📦",
    "reports": "📊",
    "sellers": "👤",
    "statuses": "📊",
    "settings": "⚙️",
}


def _topics_keyboard():
    buttons = []
    row = []
    for topic in sorted(HELP_TOPICS.keys()):
        emoji = TOPIC_EMOJIS.get(topic, "📖")
        row.append(InlineKeyboardButton(
            f"{emoji} {topic.title()}",
            callback_data=f"help:{topic}",
        ))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    args = context.args
    role = get_user_role(update.effective_user.id)
    if not args:
        text = HELP_MAIN_ADMIN if role == "admin" else HELP_MAIN_SELLER
        kb = _topics_keyboard()
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)
        return
    topic = args[0].lower().lstrip("/")
    if topic in HELP_TOPICS:
        emoji = TOPIC_EMOJIS.get(topic, "📖")
        kb = _topics_keyboard()
        await update.message.reply_text(HELP_TOPICS[topic], parse_mode="HTML", reply_markup=kb)
    else:
        kb = _topics_keyboard()
        await update.message.reply_text(
            f"⚠️ Unknown topic: {esc(topic)}\n\nTap a topic below:",
            parse_mode="HTML",
            reply_markup=kb,
        )


async def handle_help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, topic):
    query = update.callback_query
    if topic in HELP_TOPICS:
        emoji = TOPIC_EMOJIS.get(topic, "📖")
        kb = _topics_keyboard()
        await query.edit_message_text(HELP_TOPICS[topic], parse_mode="HTML", reply_markup=kb)
    else:
        await query.answer("⚠️ Unknown topic", show_alert=True)
