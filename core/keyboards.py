from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database.categories import list_categories
from core.format import esc


def category_keyboard(callback_prefix, include_all=False, status=None):
    cats = list_categories(status=status)
    buttons = []
    row = []
    if include_all:
        row.append(InlineKeyboardButton("📋 All", callback_data=f"{callback_prefix}:all"))
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
                InlineKeyboardButton("📋 List", callback_data="menu:list"),
                InlineKeyboardButton("🔎 Search", callback_data="menu:search"),
            ],
            [
                InlineKeyboardButton("📈 Sales", callback_data="menu:sales"),
                InlineKeyboardButton("📦 Inventory", callback_data="menu:inventory"),
                InlineKeyboardButton("👥 Sellers", callback_data="menu:sellers"),
            ],
            [
                InlineKeyboardButton("📊 Report", callback_data="menu:report"),
                InlineKeyboardButton("⚙️ Settings", callback_data="menu:settings"),
            ],
        ]
    else:
        buttons = [
            [
                InlineKeyboardButton("📋 List", callback_data="menu:list"),
                InlineKeyboardButton("🔎 Search", callback_data="menu:search"),
            ],
            [
                InlineKeyboardButton("📈 Sales", callback_data="menu:sales"),
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
            InlineKeyboardButton("✅ Yes", callback_data=f"{callback_prefix}:yes"),
            InlineKeyboardButton("❌ No", callback_data=f"{callback_prefix}:no"),
        ]
    ])


def add_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👤 Single", callback_data="menu:add:single"),
            InlineKeyboardButton("📥 Bulk", callback_data="menu:add:bulk"),
        ],
        [
            InlineKeyboardButton("📄 CSV Import", callback_data="menu:add:csv"),
        ],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="menu:back"),
        ]
    ])


def settings_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Stats", callback_data="menu:stats"),
            InlineKeyboardButton("📈 Revenue", callback_data="stats:all"),
        ],
        [
            InlineKeyboardButton("📤 Export", callback_data="menu:export"),
            InlineKeyboardButton("💾 Backup", callback_data="menu:backup"),
        ],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="menu:back"),
        ]
    ])


def report_period_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📅 Today", callback_data="report:today"),
            InlineKeyboardButton("📅 This Week", callback_data="report:week"),
        ],
        [
            InlineKeyboardButton("📅 This Month", callback_data="report:month"),
            InlineKeyboardButton("📅 All Time", callback_data="report:all"),
        ]
    ])


def sell_select_keyboard(selected, accounts, page, total_pages, max_select=None, prefix="sell"):
    buttons = []
    for acc in accounts:
        a = acc if isinstance(acc, dict) else dict(acc)
        mark = "✅" if a["id"] in selected else "  "
        buttons.append([
            InlineKeyboardButton(
                f"{mark} #{a['id']} | {esc(a['username'])}",
                callback_data=f"{prefix}toggle:{a['id']}",
            )
        ])
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"{prefix}page:{page - 1}"))
    nav_row.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("➡️", callback_data=f"{prefix}page:{page + 1}"))
    buttons.append(nav_row)
    limit_text = " (max 1)" if max_select == 1 else ""
    buttons.append([
        InlineKeyboardButton(
            f"✅ Done ({len(selected)} selected){limit_text}",
            callback_data=f"{prefix}done",
        ),
        InlineKeyboardButton("❌ Cancel", callback_data=f"{prefix}cancel"),
    ])
    return InlineKeyboardMarkup(buttons)
