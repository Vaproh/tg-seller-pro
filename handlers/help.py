from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.permissions import require_seller, get_user_role
from core.format import esc
from core.help_content import HELP_MAIN_ADMIN, HELP_MAIN_SELLER, HELP_TOPICS


TOPIC_EMOJIS = {
    "sell": "💰", "bulksell": "💰", "sales": "📈", "sale": "🧾",
    "markpaid": "💳", "marksold": "🔴", "markunsold": "🟢",
    "markpendingpayment": "🟡", "voidsale": "♻️",
    "list": "📋", "search": "🔎", "getid": "🔍",
    "add": "➕", "bulkadd": "📥", "extractcsv": "📄",
    "delete": "🗑️", "bulkdelete": "🗑️",
    "preview": "📂", "categories": "📂", "addcategory": "➕",
    "deletecategory": "🗑️",
    "inventory": "📦", "buyers": "👥", "buyer": "👤",
    "report": "📊", "addseller": "👤", "removeseller": "🚫",
    "listsellers": "👥", "export": "📤", "backup": "💾",
    "ping": "🏓", "status": "📊", "filter": "🔍", "settings": "⚙️",
}

TOPIC_NAMES = {
    "sell": "Sell", "bulksell": "Bulk Sell", "sales": "Sales", "sale": "Sale",
    "markpaid": "Mark Paid", "marksold": "Mark Sold", "markunsold": "Mark Unsold",
    "markpendingpayment": "Mark Pending", "voidsale": "Void Sale",
    "list": "List", "search": "Search", "getid": "Get ID",
    "add": "Add Account", "bulkadd": "Bulk Add", "extractcsv": "CSV Export",
    "delete": "Delete", "bulkdelete": "Bulk Delete",
    "preview": "Preview", "categories": "Categories", "addcategory": "Add Category",
    "deletecategory": "Delete Category",
    "inventory": "Inventory", "buyers": "Buyers", "buyer": "Buyer",
    "report": "Report", "addseller": "Add Seller", "removeseller": "Remove Seller",
    "listsellers": "List Sellers", "export": "Export", "backup": "Backup",
    "ping": "Ping", "status": "Status", "filter": "Filter", "settings": "Settings",
}

COMMAND_TO_TOPIC = {
    "sell": "sell", "bulksell": "bulksell", "sales": "sales", "sale": "sale",
    "markpaid": "markpaid", "marksold": "marksold", "markunsold": "markunsold",
    "markpendingpayment": "markpendingpayment", "voidsale": "voidsale",
    "list": "list", "search": "search", "getid": "getid",
    "add": "add", "bulkadd": "bulkadd", "extractcsv": "extractcsv",
    "delete": "delete", "bulkdelete": "bulkdelete",
    "preview": "preview", "categories": "categories", "addcategory": "addcategory",
    "deletecategory": "deletecategory",
    "inventory": "inventory", "buyers": "buyers", "buyer": "buyer",
    "report": "report", "addseller": "addseller", "removeseller": "removeseller",
    "listsellers": "listsellers", "export": "export", "backup": "backup",
    "ping": "ping",
}


def _topics_keyboard():
    buttons = []
    row = []
    topics = ["sell", "bulksell", "list", "search", "add", "delete",
              "status", "filter", "preview", "inventory",
              "sales", "buyers", "categories", "settings"]
    for topic in topics:
        if topic not in HELP_TOPICS:
            continue
        emoji = TOPIC_EMOJIS.get(topic, "📖")
        name = TOPIC_NAMES.get(topic, topic.title())
        row.append(InlineKeyboardButton(
            f"{emoji} {name}",
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
    cmd = args[0].lower().lstrip("/")
    topic = COMMAND_TO_TOPIC.get(cmd, cmd)
    if topic in HELP_TOPICS:
        kb = _topics_keyboard()
        await update.message.reply_text(HELP_TOPICS[topic], parse_mode="HTML", reply_markup=kb)
    else:
        kb = _topics_keyboard()
        await update.message.reply_text(
            f"⚠️ No help for '{esc(cmd)}'.\n\nTap a topic below:",
            parse_mode="HTML",
            reply_markup=kb,
        )


async def handle_help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, topic):
    query = update.callback_query
    if topic in HELP_TOPICS:
        kb = _topics_keyboard()
        await query.edit_message_text(HELP_TOPICS[topic], parse_mode="HTML", reply_markup=kb)
    else:
        await query.answer("⚠️ Unknown topic", show_alert=True)
