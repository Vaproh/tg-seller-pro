from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from core.format import esc, _d, reddit_url, code_id, code_username
from database import list_accounts, count_accounts, list_categories, get_category_name
import config


PAGE_SIZE = 5
MAX_MSG_LEN = 4000


def parse_id_list(text):
    if not text or not text.strip():
        return None
    ids = []
    for part in text.replace(" ", ",").split(","):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))
    return ids if ids else None


def parse_filter_state(filter_str):
    if not filter_str:
        return {}
    result = {}
    for part in filter_str.split("|"):
        if ":" in part:
            k, v = part.split(":", 1)
            result[k] = v
    return result


def build_filter_state(status=None, category_id=None, id_list=None):
    parts = []
    if status:
        parts.append(f"status:{status}")
    if category_id:
        parts.append(f"cat:{category_id}")
    if id_list:
        parts.append(f"ids:{','.join(str(i) for i in id_list)}")
    return "|".join(parts) if parts else None


def apply_list_filters(filter_str, limit=PAGE_SIZE, offset=0):
    f = parse_filter_state(filter_str)
    status = f.get("status")
    cat_id = int(f["cat"]) if "cat" in f else None
    id_list = [int(x) for x in f["ids"].split(",")] if "ids" in f else None
    accounts = list_accounts(
        limit=limit, offset=offset,
        status=status, category_id=cat_id, id_list=id_list,
    )
    total = count_accounts(status=status, category_id=cat_id, id_list=id_list)
    return accounts, total


def count_from_filter(filter_str):
    f = parse_filter_state(filter_str)
    status = f.get("status")
    cat_id = int(f["cat"]) if "cat" in f else None
    id_list = [int(x) for x in f["ids"].split(",")] if "ids" in f else None
    return count_accounts(status=status, category_id=cat_id, id_list=id_list)


def fmt_account_list_line(account):
    a = _d(account)
    status = a.get("status", "available")
    status_emoji = {"available": "🟢", "sold": "🔴", "pending_payment": "🟡"}.get(status, "⚪")
    return (
        f"• ID: {code_id(a.get('id', ''))}  |  "
        f"User: {code_username(a.get('username'))}  |  "
        f"{status_emoji} {esc(status)}  |  "
        f"{esc(a.get('category_name', '—'))}"
    )


def fmt_account_list_page(accounts, page, total_pages, title="Accounts"):
    text = f"<b>📋 {title}  page {page}/{total_pages}</b>\n\n"
    for acc in accounts:
        text += fmt_account_list_line(acc) + "\n"
    if not accounts:
        text += "📭 No accounts found."
    return text


def filter_keyboard(prefix, include_available=True, include_sold=True,
                    include_pending=False, include_all=True, include_ids=False):
    buttons = []
    row = []
    if include_all:
        row.append(InlineKeyboardButton("📋 All", callback_data=f"{prefix}:all"))
    if include_available:
        row.append(InlineKeyboardButton("🟢 Available", callback_data=f"{prefix}:available"))
    if include_sold:
        row.append(InlineKeyboardButton("🔴 Sold", callback_data=f"{prefix}:sold"))
    if include_pending:
        row.append(InlineKeyboardButton("🟡 Pending", callback_data=f"{prefix}:pending"))
    if row:
        buttons.append(row)
    cat_row = [
        InlineKeyboardButton("📂 Category", callback_data=f"{prefix}cat"),
    ]
    if include_ids:
        cat_row.append(InlineKeyboardButton("🔢 By ID", callback_data=f"{prefix}ids"))
    buttons.append(cat_row)
    return InlineKeyboardMarkup(buttons)


def pagination_row(prefix, page, total_pages):
    row = []
    if page > 1:
        row.append(InlineKeyboardButton("⬅️", callback_data=f"{prefix}:{page - 1}"))
    row.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        row.append(InlineKeyboardButton("➡️", callback_data=f"{prefix}:{page + 1}"))
    return row


def filter_page_keyboard(prefix, page, total_pages, **filter_kwargs):
    filter_row_buttons = []
    if filter_kwargs.get("include_all", True):
        filter_row_buttons.append(InlineKeyboardButton("📋 All", callback_data=f"{prefix}:all"))
    if filter_kwargs.get("include_available", True):
        filter_row_buttons.append(InlineKeyboardButton("🟢 Available", callback_data=f"{prefix}:available"))
    if filter_kwargs.get("include_sold", True):
        filter_row_buttons.append(InlineKeyboardButton("🔴 Sold", callback_data=f"{prefix}:sold"))
    if filter_kwargs.get("include_pending"):
        filter_row_buttons.append(InlineKeyboardButton("🟡 Pending", callback_data=f"{prefix}:pending"))

    cat_row = [InlineKeyboardButton("📂 Category", callback_data=f"{prefix}cat")]
    if filter_kwargs.get("include_ids"):
        cat_row.append(InlineKeyboardButton("🔢 By ID", callback_data=f"{prefix}ids"))

    nav_row = pagination_row(f"{prefix}page", page, total_pages)

    return InlineKeyboardMarkup([filter_row_buttons, cat_row, nav_row])


def category_keyboard_with_all(callback_prefix):
    cats = list_categories()
    buttons = []
    row = [InlineKeyboardButton("📋 All", callback_data=f"{callback_prefix}:all")]
    buttons.append(row)
    row = []
    for cat in cats:
        label = f"{cat['name']} ({cat['account_count']})"
        row.append(InlineKeyboardButton(label, callback_data=f"{callback_prefix}:{cat['id']}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons) if buttons else None


def buyer_keyboard(buyer_names, callback_prefix="buypick"):
    buttons = []
    for name in buyer_names[:10]:
        buttons.append([
            InlineKeyboardButton(
                f"👤 {esc(name)}",
                callback_data=f"{callback_prefix}:{name}",
            )
        ])
    buttons.append([
        InlineKeyboardButton("✏️ Type new buyer", callback_data=f"{callback_prefix}:new")
    ])
    return InlineKeyboardMarkup(buttons)


def payment_status_keyboard(prefix="paystatus"):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔴 Sold", callback_data=f"{prefix}:sold"),
        ],
        [
            InlineKeyboardButton("🟡 Pending Payment", callback_data=f"{prefix}:pending"),
        ],
    ])


def sale_actions_keyboard(sale_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Mark Paid", callback_data=f"markpaid:{sale_id}"),
            InlineKeyboardButton("🔴 Mark Unsold", callback_data=f"marksaleunsold:{sale_id}"),
        ],
        [
            InlineKeyboardButton("🟡 Mark Pending", callback_data=f"marksalepending:{sale_id}"),
            InlineKeyboardButton("♻️ Void", callback_data=f"sellervoidconfirm:{sale_id}"),
        ],
    ])


def mark_status_keyboard(callback_prefix):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟢 Available", callback_data=f"{callback_prefix}:available"),
            InlineKeyboardButton("🔴 Sold", callback_data=f"{callback_prefix}:sold"),
        ],
        [
            InlineKeyboardButton("🟡 Pending Payment", callback_data=f"{callback_prefix}:pending_payment"),
        ],
    ])
