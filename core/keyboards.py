from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database.categories import list_categories


def category_keyboard(callback_prefix, include_all=False):
    cats = list_categories()
    buttons = []
    row = []
    if include_all:
        row.append(InlineKeyboardButton("All", callback_data=f"{callback_prefix}:all"))
    for cat in cats:
        label = f"{cat['name']} ({cat['account_count']})"
        row.append(InlineKeyboardButton(label, callback_data=f"{callback_prefix}:{cat['id']}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons) if buttons else None


def main_menu_keyboard(is_admin=True):
    if is_admin:
        buttons = [
            [
                InlineKeyboardButton("➕ Add", callback_data="menu:add"),
                InlineKeyboardButton("💰 Sell", callback_data="menu:sell"),
                InlineKeyboardButton("📋 List", callback_data="menu:list"),
            ],
            [
                InlineKeyboardButton("🔎 Search", callback_data="menu:search"),
                InlineKeyboardButton("📈 Sales", callback_data="menu:sales"),
                InlineKeyboardButton("📦 Inventory", callback_data="menu:inventory"),
            ],
            [
                InlineKeyboardButton("👥 Sellers", callback_data="menu:sellers"),
                InlineKeyboardButton("📊 Report", callback_data="menu:report"),
                InlineKeyboardButton("⚙️ Settings", callback_data="menu:settings"),
            ],
        ]
    else:
        buttons = [
            [
                InlineKeyboardButton("💰 Sell", callback_data="menu:sell"),
                InlineKeyboardButton("📋 List", callback_data="menu:list"),
            ],
            [
                InlineKeyboardButton("🔎 Search", callback_data="menu:search"),
                InlineKeyboardButton("📈 Sales", callback_data="menu:sales"),
            ],
            [
                InlineKeyboardButton("📦 Inventory", callback_data="menu:inventory"),
            ],
        ]
    return InlineKeyboardMarkup(buttons)


def confirm_keyboard(confirm_data, cancel_data):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm", callback_data=confirm_data),
            InlineKeyboardButton("❌ Cancel", callback_data=cancel_data),
        ]
    ])


def yes_no_keyboard(callback_prefix):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Yes", callback_data=f"{callback_prefix}:yes"),
            InlineKeyboardButton("No", callback_data=f"{callback_prefix}:no"),
        ]
    ])


def add_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Single", callback_data="menu:add:single"),
            InlineKeyboardButton("Bulk", callback_data="menu:add:bulk"),
        ],
        [
            InlineKeyboardButton("CSV Import", callback_data="menu:add:csv"),
        ],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="menu:back"),
        ]
    ])


def settings_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Stats", callback_data="menu:stats"),
            InlineKeyboardButton("📤 Export", callback_data="menu:export"),
        ],
        [
            InlineKeyboardButton("💾 Backup", callback_data="menu:backup"),
        ],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="menu:back"),
        ]
    ])


def report_period_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Today", callback_data="report:today"),
            InlineKeyboardButton("This Week", callback_data="report:week"),
        ],
        [
            InlineKeyboardButton("This Month", callback_data="report:month"),
            InlineKeyboardButton("All Time", callback_data="report:all"),
        ]
    ])
