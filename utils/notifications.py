import logging
from telegram import Bot
from config import ADMIN_USER_ID

logger = logging.getLogger(__name__)


async def notify_admin(context, message):
    try:
        await context.bot.send_message(chat_id=ADMIN_USER_ID, text=message, parse_mode="HTML")
    except Exception as e:
        logger.error("Failed to notify admin: %s", e)


def fmt_sale_notification(sale):
    return (
        f"💰 New sale! #{sale['id']} — "
        f"{sale['buyer_name']} — ₹{sale['price']:.0f} — "
        f"by {sale.get('seller_name', '—')}"
    )


def fmt_payment_notification(sale):
    return (
        f"✅ Payment received! Sale #{sale['id']} — "
        f"₹{sale['price']:.0f} from {sale['buyer_name']}"
    )


def fmt_high_value_notification(sale):
    return (
        f"🔥 High-value sale! #{sale['id']} — "
        f"₹{sale['price']:.0f} from {sale['buyer_name']} — "
        f"by {sale.get('seller_name', '—')}"
    )


def fmt_void_notification(sale_id):
    return f"♻️ Sale #{sale_id} voided — account returned to stock"


def fmt_seller_added(name, user_id):
    return f"👤 New seller: {name} (ID: {user_id})"


def fmt_seller_removed(name, user_id):
    return f"🚫 Seller removed: {name} (ID: {user_id})"


def fmt_bulk_import(added, skipped, category):
    return f"📥 Bulk import: {added} added, {skipped} skipped in {category}"


def fmt_status_change(account_id, old_status, new_status):
    return f"⚠️ Account #{account_id} status: {old_status} → {new_status}"
