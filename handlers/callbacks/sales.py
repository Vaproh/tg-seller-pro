from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.permissions import require_seller, get_user_role
from core.state import state
from core.format import _d, _truncate, esc, code, code_id
from core.keyboards import confirm_keyboard
from core.filters import PAGE_SIZE
from database import get_sale_by_id, count_sales, get_sales, get_seller_by_user_id, mark_payment, void_sale
from database.sales import update_sale, get_sales_summary
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
        summary = get_sales_summary(seller_id=seller_id)
        text = _fmt_sales_page(sales, 1, total_pages, summary=summary)
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
        summary = get_sales_summary(seller_id=seller_id, period=status_val)
        text = _fmt_sales_page(sales, 1, total_pages, summary=summary)
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
        summary = get_sales_summary(seller_id=seller_id, period=sf)
        text = _fmt_sales_page(sales, page, total_pages, summary=summary)
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
        label = "paid ✅" if new_status == "paid" else "🟡 pending"
        sale_code = _d(sale).get("sale_code", f"#{sale_id}")
        await query.edit_message_text(f"✅ {code(sale_code)} → {label}.")
        if new_status == "paid":
            await notify_admin(context, f"✅ Payment received! {code(sale_code)} — ₹{_d(sale).get('price', 0):.0f} from {_d(sale).get('buyer_name')}")
        return True

    if data.startswith("marksold:"):
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
            await query.edit_message_text("⚠️ You can only modify your own sales.")
            return True
        mark_payment(sale_id, "paid")
        sale_code = sd.get("sale_code", f"#{sale_id}")
        await query.edit_message_text(f"✅ {code(sale_code)} → 🔴 sold.")
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
            f"⚠️ Void sale {code_id(sale_id)}? Account will return to available stock.",
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
            f"⚠️ Void sale {code_id(sale_id)}? Account will return to available stock.",
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
        sd = _d(sale)
        role = get_user_role(user_id)
        if role != "admin" and sd.get("seller_user_id") != user_id:
            await query.edit_message_text("⚠️ You can only modify your own sales.")
            return True
        mark_payment(sale_id, "pending")
        sale_code = sd.get("sale_code", f"#{sale_id}")
        await query.edit_message_text(f"✅ {code(sale_code)} → 🟡 pending payment.")
        return True

    if data.startswith("voidconfirm:"):
        if not await require_seller(update):
            return True
        try:
            sale_id = int(data.split(":")[1])
        except ValueError:
            return True
        state.pop(user_id, "void_confirm", None)
        sale = get_sale_by_id(sale_id)
        sale_code = _d(sale).get("sale_code", f"#{sale_id}") if sale else f"#{sale_id}"
        success = void_sale(sale_id)
        if success:
            await query.edit_message_text(f"✅ {code(sale_code)} voided. Account returned to available stock.")
            await notify_admin(context, fmt_void_notification(sale_code))
        else:
            await query.edit_message_text("❌ Failed to void sale.")
        return True

    if data == "voidcancel":
        state.pop(user_id, "void_confirm", None)
        await query.edit_message_text("❌ Void cancelled.")
        return True

    if data.startswith("editsale:mode:"):
        mode = data.split(":")[-1]
        state.set(user_id, "editsale_mode", mode)
        if mode == "sale":
            prompt = "🏷️ Enter sale ID(s), comma-separated:\n(e.g. SALE-X7K9M2P4)"
        else:
            prompt = "📦 Enter account ID(s), comma-separated:\n(e.g. 1,2,3)"
        state.set(user_id, "editsale_stage", "awaiting_ids")
        await query.edit_message_text(prompt)
        return True

    if data.startswith("editsale:field:"):
        field = data.split(":")[-1]
        state.set(user_id, "editsale_field", field)
        prompts = {
            "buyer": "👤 Enter new buyer name:",
            "price": "💰 Enter new price (₹):",
            "status": None,
            "notes": "📝 Enter new notes (or /clear to remove):",
        }
        if field == "status":
            kb = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Paid", callback_data="editsale:set:paid"),
                    InlineKeyboardButton("🟡 Pending", callback_data="editsale:set:pending"),
                ],
                [InlineKeyboardButton("❌ Back", callback_data="editsale:back")],
            ])
            await query.edit_message_text("📦 Select new payment status:", reply_markup=kb)
        else:
            await query.edit_message_text(prompts[field])
        return True

    if data == "editsale:back":
        pending = state.get(user_id, "editsale_pending", {})
        sale_ids = state.get(user_id, "editsale_ids", [])
        sales = []
        for sid in sale_ids:
            sale = get_sale_by_id(sid)
            if sale:
                sales.append(_d(sale))
        from handlers.sell import _editsale_summary_with_pending, _editsale_field_keyboard
        text = _editsale_summary_with_pending(sales, pending)
        if pending:
            text += "\n\n<b>Pending changes:</b>\n"
            for sid, fields in pending.items():
                parts = ", ".join(f"{k}={v}" for k, v in fields.items())
                text += f"• {code_id(sid)}: {parts}\n"
        kb = _editsale_field_keyboard()
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return True

    if data.startswith("editsale:set:"):
        value = data.split(":")[-1]
        field = state.get(user_id, "editsale_field")
        sale_ids = state.get(user_id, "editsale_ids", [])
        pending = state.get(user_id, "editsale_pending", {})
        field_key = "buyer_name" if field == "buyer" else ("payment_status" if field == "status" else field)
        for sid in sale_ids:
            if sid not in pending:
                pending[sid] = {}
            pending[sid][field_key] = value
        state.set(user_id, "editsale_pending", pending)
        state.pop(user_id, "editsale_field")
        from handlers.sell import _editsale_summary_with_pending, _editsale_field_keyboard
        sales = []
        for sid in sale_ids:
            sale = get_sale_by_id(sid)
            if sale:
                sales.append(_d(sale))
        text = _editsale_summary_with_pending(sales, pending)
        text += f"\n\n✅ Set {field} → <code>{esc(value)}</code> for all {len(sale_ids)} sale(s)"
        kb = _editsale_field_keyboard()
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=kb)
        return True

    if data == "editsale:done":
        pending = state.get(user_id, "editsale_pending", {})
        sale_ids = state.get(user_id, "editsale_ids", [])
        state.pop(user_id, "editsale_ids")
        state.pop(user_id, "editsale_pending")
        state.pop(user_id, "editsale_field")
        if not pending:
            await query.edit_message_text("ℹ️ No changes to apply.")
            return True
        updated, failed = [], []
        for sid in sale_ids:
            if sid in pending:
                if update_sale(sid, **pending[sid]):
                    updated.append(sid)
                else:
                    failed.append(sid)
        parts = []
        if updated:
            field_names = set()
            for fields in pending.values():
                field_names.update(fields.keys())
            sale = get_sale_by_id(updated[0])
            sale_code = _d(sale).get("sale_code", f"#{updated[0]}") if sale else f"#{updated[0]}"
            if len(updated) > 1:
                parts.append(f"✏️ Updated {len(updated)} sales: {', '.join(field_names)}")
            else:
                parts.append(f"✏️ Updated {code(sale_code)}: {', '.join(field_names)}")
        if failed:
            parts.append(f"⚠️ Failed: {', '.join(code(i) for i in failed)}")
        await query.edit_message_text("\n".join(parts))
        return True

    if data == "editsale:cancel":
        state.pop(user_id, "editsale_ids")
        state.pop(user_id, "editsale_pending")
        state.pop(user_id, "editsale_field")
        await query.edit_message_text("❌ Edit cancelled.")
        return True

    return False
