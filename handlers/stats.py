from telegram import Update, InputFile
from telegram.ext import ContextTypes
from core.permissions import require_seller, get_user_role
from core.state import state
from core.format import _truncate, _d, esc
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from database import get_seller_by_user_id
from database.sales import (
    get_sales_summary, get_revenue_by_day, get_sales_by_category,
    get_top_buyers, get_top_sellers, get_payment_breakdown,
)
from utils.charts import (
    revenue_chart, category_pie, top_buyers_bar,
    payment_donut, top_sellers_bar,
)
import config


def _stats_period_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Today", callback_data="stats:today"),
            InlineKeyboardButton("This Week", callback_data="stats:week"),
        ],
        [
            InlineKeyboardButton("This Month", callback_data="stats:month"),
            InlineKeyboardButton("All Time", callback_data="stats:all"),
        ],
        [
            InlineKeyboardButton("📊 Charts", callback_data="stats:charts"),
        ],
    ])


def _fmt_summary(s, period_label):
    if not s:
        return f"📊 <b>Statistics — {period_label}</b>\n\n📭 No sales data."
    avg = s["total_revenue"] / s["total_sales"] if s["total_sales"] else 0
    return (
        f"📊 <b>Statistics — {period_label}</b>\n\n"
        f"💰 <b>Revenue:</b> {config.CURRENCY}{s['total_revenue']:.0f}\n"
        f"📦 <b>Total Sales:</b> {s['total_sales']}\n"
        f"💰 <b>Avg Sale:</b> {config.CURRENCY}{avg:.0f}\n"
        f"🟡 <b>Pending:</b> {s['pending_count']} sales ({config.CURRENCY}{s['pending_amount']:.0f})\n"
        f"✅ <b>Paid:</b> {s['total_sales'] - s['pending_count']} sales"
    )


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_seller(update):
        return
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    seller = get_seller_by_user_id(user_id) if role != "admin" else None
    seller_id = seller["id"] if seller else None

    period = None
    period_label = "All Time"
    if context.args:
        arg = context.args[0].lower()
        if arg in ("today", "day"):
            period, period_label = "today", "Today"
        elif arg in ("week",):
            period, period_label = "week", "This Week"
        elif arg in ("month",):
            period, period_label = "month", "This Month"

    summary = get_sales_summary(seller_id=seller_id, period=period)
    text = _fmt_summary(summary, period_label)
    kb = _stats_period_keyboard()
    await update.message.reply_text(_truncate(text), parse_mode="HTML", reply_markup=kb)


async def stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str, user_id: int) -> bool:
    query = update.callback_query

    if not data.startswith("stats:"):
        return False

    action = data.split(":", 1)[1]

    role = get_user_role(user_id)
    seller = get_seller_by_user_id(user_id) if role != "admin" else None
    seller_id = seller["id"] if seller else None

    if action in ("today", "week", "month", "all"):
        period_map = {"today": "today", "week": "week", "month": "month", "all": None}
        label_map = {"today": "Today", "week": "This Week", "month": "This Month", "all": "All Time"}
        period = period_map[action]
        label = label_map[action]
        summary = get_sales_summary(seller_id=seller_id, period=period)
        text = _fmt_summary(summary, label)
        state.set(user_id, "stats_period", action)
        await query.edit_message_text(_truncate(text), parse_mode="HTML", reply_markup=_stats_period_keyboard())
        return True

    if action == "charts":
        period = state.get(user_id, "stats_period", "all")
        period_map = {"today": "today", "week": "week", "month": "month", "all": None}
        days_map = {"today": 1, "week": 7, "month": 30, "all": 90}
        p = period_map.get(period)
        days = days_map.get(period, 90)

        await query.edit_message_text("📊 Generating charts...")

        charts = []

        rows = get_revenue_by_day(days=days, seller_id=seller_id)
        buf = revenue_chart(rows)
        if buf:
            charts.append(buf)

        rows = get_sales_by_category(seller_id=seller_id)
        buf = category_pie(rows)
        if buf:
            charts.append(buf)

        rows = get_payment_breakdown(seller_id=seller_id)
        buf = payment_donut(rows)
        if buf:
            charts.append(buf)

        rows = get_top_buyers(limit=10, seller_id=seller_id)
        buf = top_buyers_bar(rows)
        if buf:
            charts.append(buf)

        if role == "admin":
            rows = get_top_sellers(limit=10)
            buf = top_sellers_bar(rows)
            if buf:
                charts.append(buf)

        if not charts:
            await query.edit_message_text("📭 No data to generate charts.")
            return True

        for i, buf in enumerate(charts):
            buf.seek(0)
            caption = None
            if i == 0:
                caption = "📈 Revenue Over Time"
            elif i == 1:
                caption = "📂 By Category"
            elif i == 2:
                caption = "💳 Payment Status"
            elif i == 3:
                caption = "🏆 Top Buyers"
            elif i == 4:
                caption = "👨‍💼 Top Sellers"
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=buf,
                caption=caption,
            )

        kb = _stats_period_keyboard()
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="📊 Charts complete. Pick another period or generate again:",
            reply_markup=kb,
        )
        return True

    return False
