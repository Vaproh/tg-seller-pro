import logging
from telegram import Bot
from core.format import code_id, code
from config import ADMIN_USER_ID

logger = logging.getLogger(__name__)


async def notify_admin(context, message):
    try:
        await context.bot.send_message(chat_id=ADMIN_USER_ID, text=message, parse_mode="HTML")
    except Exception as e:
        logger.error("Failed to notify admin: %s", e)


def fmt_sale_notification(sale):
    sale_code = sale.get("sale_code", f"#{sale['id']}")
    return (
        f"💰 New sale! {code(sale_code)} — "
        f"{code(sale['buyer_name'])} — ₹{sale['price']:.0f} — "
        f"by {sale.get('seller_name', '—')}"
    )


def fmt_payment_notification(sale):
    sale_code = sale.get("sale_code", f"#{sale['id']}")
    return (
        f"✅ Payment received! {code(sale_code)} — "
        f"₹{sale['price']:.0f} from {code(sale['buyer_name'])}"
    )


def fmt_high_value_notification(sale):
    sale_code = sale.get("sale_code", f"#{sale['id']}")
    return (
        f"🔥 High-value sale! {code(sale_code)} — "
        f"₹{sale['price']:.0f} from {code(sale['buyer_name'])} — "
        f"by {sale.get('seller_name', '—')}"
    )


def fmt_void_notification(sale_code):
    return f"♻️ {code(sale_code)} voided — account returned to stock"


def fmt_seller_added(name, user_id):
    return f"👤 New seller: {name} (ID: {code_id(user_id)})"


def fmt_seller_removed(name, user_id):
    return f"🚫 Seller removed: {name} (ID: {code_id(user_id)})"


def fmt_bulk_import(added, skipped, category):
    return f"📥 Bulk import: {added} added, {skipped} skipped in {code(category)}"


def fmt_status_change(account_id, old_status, new_status):
    return f"⚠️ Account {code_id(account_id)} status: {old_status} → {new_status}"
