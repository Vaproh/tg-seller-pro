from telegram import Update
from telegram.ext import ContextTypes
from core.permissions import require_seller, get_user_role
from core.state import state
from core.format import _d, _truncate
from core.keyboards import confirm_keyboard
from core.filters import PAGE_SIZE
from database import get_sale_by_id, count_sales, get_sales, get_seller_by_user_id, mark_payment, void_sale
from utils.notifications import notify_admin, fmt_void_notification


async def try_handle(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str, user_id: int) -> bool:
    query = update.callback_query

    if data == "menu:sales":
        if not await require_seller(update):
            return True
        role = get_user_role(user_id)
        seller = get_seller_by_user_id(user_id) if role != "admin" else None
        seller_id = seller["id"] if seller else None
        state.set(user_id, "sales_page", 1)
        state.set(user_id, "sales_filter", None)
        total = count_sales(seller_id=seller_id)
        if total == 0:
            await query.edit_message_text("📭 No sales found.")
            return True
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        sales = get_sales(limit=PAGE_SIZE, offset=0, seller_id=seller_id)
        from handlers.sell import _fmt_sales_page, _sales_keyboard
        text = _fmt_sales_page(sales, 1, total_pages)
        kb = _sales_keyboard(1, total_pages)
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return True

    if data.startswith("salesfilter:") and not data.startswith("salesfilterpage:"):
        if not await require_seller(update):
            return True
        f = data.split(":", 1)[1]
        state.set(user_id, "sales_filter", f)
        state.set(user_id, "sales_page", 1)
        role = get_user_role(user_id)
        seller = get_seller_by_user_id(user_id) if role != "admin" else None
        seller_id = seller["id"] if seller else None
        status_val = f if f != "all" else None
        total = count_sales(seller_id=seller_id, status=status_val)
        if total == 0:
            await query.edit_message_text("📭 No sales found.")
            return True
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        sales = get_sales(limit=PAGE_SIZE, offset=0, seller_id=seller_id, status=status_val)
        from handlers.sell import _fmt_sales_page, _sales_keyboard
        text = _fmt_sales_page(sales, 1, total_pages)
        kb = _sales_keyboard(1, total_pages)
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return True

    if data.startswith("salesfilterpage:"):
        if not await require_seller(update):
            return True
        try:
            page = int(data.split(":")[1])
        except ValueError:
            return True
        role = get_user_role(user_id)
        seller = get_seller_by_user_id(user_id) if role != "admin" else None
        seller_id = seller["id"] if seller else None
        sf = state.get(user_id, "sales_filter")
        status_val = sf if sf and sf != "all" else None
        total = count_sales(seller_id=seller_id, status=status_val)
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = max(1, min(page, total_pages))
        state.set(user_id, "sales_page", page)
        sales = get_sales(limit=PAGE_SIZE, offset=(page - 1) * PAGE_SIZE, seller_id=seller_id, status=status_val)
        from handlers.sell import _fmt_sales_page, _sales_keyboard
        text = _fmt_sales_page(sales, page, total_pages)
        kb = _sales_keyboard(page, total_pages)
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return True

    if data.startswith("markpaid:"):
        if not await require_seller(update):
            return True
        try:
            sale_id = int(data.split(":")[1])
        except ValueError:
            return True
        sale = get_sale_by_id(sale_id)
        if not sale:
            await query.edit_message_text("🔍 Sale not found.")
            return True
        role = get_user_role(user_id)
        if role != "admin" and _d(sale).get("seller_user_id") != user_id:
            await query.edit_message_text("⚠️ You can only mark your own sales as paid.")
            return True
        new_status = "paid" if _d(sale).get("payment_status") == "pending" else "pending"
        mark_payment(sale_id, new_status)
        label = "paid" if new_status == "paid" else "pending"
        await query.edit_message_text(f"✅ Sale #{sale_id} marked as {label}.")
        if new_status == "paid":
            await notify_admin(context, f"✅ Payment received! Sale #{sale_id} — ₹{_d(sale).get('price', 0):.0f} from {_d(sale).get('buyer_name')}")
        return True

    if data.startswith("marksaleunsold:"):
        if not await require_seller(update):
            return True
        try:
            sale_id = int(data.split(":")[1])
        except ValueError:
            return True
        sale = get_sale_by_id(sale_id)
        if not sale:
            await query.edit_message_text("🔍 Sale not found.")
            return True
        sd = _d(sale)
        role = get_user_role(user_id)
        if role != "admin" and sd.get("seller_user_id") != user_id:
            await query.edit_message_text("⚠️ You can only void your own sales.")
            return True
        state.set(user_id, "void_confirm", sale_id)
        await query.edit_message_text(
            f"⚠️ Void sale #{sale_id}? Account will return to available stock.",
            reply_markup=confirm_keyboard(f"voidconfirm:{sale_id}", "voidcancel"),
        )
        return True

    if data.startswith("sellervoidconfirm:"):
        if not await require_seller(update):
            return True
        try:
            sale_id = int(data.split(":")[1])
        except ValueError:
            return True
        sale = get_sale_by_id(sale_id)
        if not sale:
            await query.edit_message_text("🔍 Sale not found.")
            return True
        sd = _d(sale)
        role = get_user_role(user_id)
        if role != "admin" and sd.get("seller_user_id") != user_id:
            await query.edit_message_text("⚠️ You can only void your own sales.")
            return True
        state.set(user_id, "void_confirm", sale_id)
        await query.edit_message_text(
            f"⚠️ Void sale #{sale_id}? Account will return to available stock.",
            reply_markup=confirm_keyboard(f"voidconfirm:{sale_id}", "voidcancel"),
        )
        return True

    if data.startswith("marksalepending:"):
        if not await require_seller(update):
            return True
        try:
            sale_id = int(data.split(":")[1])
        except ValueError:
            return True
        sale = get_sale_by_id(sale_id)
        if not sale:
            await query.edit_message_text("🔍 Sale not found.")
            return True
        mark_payment(sale_id, "pending")
        await query.edit_message_text(f"✅ Sale #{sale_id} marked as 🟡 pending payment.")
        return True

    if data.startswith("voidconfirm:"):
        if not await require_seller(update):
            return True
        try:
            sale_id = int(data.split(":")[1])
        except ValueError:
            return True
        state.pop(user_id, "void_confirm", None)
        success = void_sale(sale_id)
        if success:
            await query.edit_message_text(f"✅ Sale #{sale_id} voided. Account returned to available stock.")
            await notify_admin(context, fmt_void_notification(sale_id))
        else:
            await query.edit_message_text("❌ Failed to void sale.")
        return True

    if data == "voidcancel":
        state.pop(user_id, "void_confirm", None)
        await query.edit_message_text("❌ Void cancelled.")
        return True

    return False
