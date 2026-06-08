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
                InlineKeyboardButton("➕ Add account", callback_data="menu:add"),
                InlineKeyboardButton("📂 Preview", callback_data="menu:preview"),
            ],
            [
                InlineKeyboardButton("💰 Sell", callback_data="menu:sell"),
                InlineKeyboardButton("📈 Sales", callback_data="menu:sales"),
            ],
            [
                InlineKeyboardButton("👥 Sellers", callback_data="menu:sellers"),
                InlineKeyboardButton("📋 List", callback_data="menu:list"),
            ],
            [
                InlineKeyboardButton("🔎 Search", callback_data="menu:search"),
                InlineKeyboardButton("📊 Report", callback_data="menu:report"),
            ],
            [
                InlineKeyboardButton("📦 Inventory", callback_data="menu:inventory"),
                InlineKeyboardButton("⚙️ Settings", callback_data="menu:settings"),
            ],
        ]
    else:
        buttons = [
            [
                InlineKeyboardButton("📂 Preview", callback_data="menu:preview"),
                InlineKeyboardButton("💰 Sell", callback_data="menu:sell"),
            ],
            [
                InlineKeyboardButton("📋 My Sales", callback_data="menu:sales"),
                InlineKeyboardButton("🔎 Search", callback_data="menu:search"),
            ],
            [
                InlineKeyboardButton("📦 Inventory", callback_data="menu:inventory"),
                InlineKeyboardButton("📋 List", callback_data="menu:list"),
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


def pagination_keyboard(callback_prefix, current_page, total_pages):
    buttons = []
    if current_page > 1:
        buttons.append(InlineKeyboardButton("⬅️", callback_data=f"{callback_prefix}:{current_page - 1}"))
    buttons.append(InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="noop"))
    if current_page < total_pages:
        buttons.append(InlineKeyboardButton("➡️", callback_data=f"{callback_prefix}:{current_page + 1}"))
    return InlineKeyboardMarkup([buttons])


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


def sale_status_keyboard(sale_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Mark Paid", callback_data=f"markpaid:{sale_id}"),
            InlineKeyboardButton("♻️ Void", callback_data=f"voidsale:{sale_id}"),
        ]
    ])


def filter_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("All", callback_data="listfilter:all"),
            InlineKeyboardButton("Available", callback_data="listfilter:available"),
            InlineKeyboardButton("Sold", callback_data="listfilter:sold"),
        ],
        [
            InlineKeyboardButton("By Category", callback_data="listfiltercat"),
        ]
    ])


def sales_filter_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("All", callback_data="salesfilter:all"),
            InlineKeyboardButton("Pending", callback_data="salesfilter:pending"),
            InlineKeyboardButton("Paid", callback_data="salesfilter:paid"),
        ]
    ])


def search_type_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Username", callback_data="search:username"),
            InlineKeyboardButton("Password", callback_data="search:password"),
        ],
        [
            InlineKeyboardButton("Category", callback_data="search:category"),
            InlineKeyboardButton("Status", callback_data="search:status"),
        ],
        [
            InlineKeyboardButton("Buyer", callback_data="search:buyer"),
            InlineKeyboardButton("Tag", callback_data="search:tag"),
        ],
        [
            InlineKeyboardButton("Notes", callback_data="search:notes"),
            InlineKeyboardButton("General", callback_data="search:general"),
        ],
    ])


def sell_accounts_keyboard(accounts, callback_prefix="sellselect"):
    buttons = []
    for acc in accounts:
        buttons.append([
            InlineKeyboardButton(
                f"#{acc['id']} | {acc['username']}",
                callback_data=f"{callback_prefix}:{acc['id']}",
            )
        ])
    return InlineKeyboardMarkup(buttons) if buttons else None


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
