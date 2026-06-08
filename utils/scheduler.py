import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import config
from database.sales import get_sales_summary, get_sales, count_sales
from database.accounts import count_accounts
from database.sellers import list_sellers

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone=config.TIMEZONE)


def _build_daily_report():
    today = get_sales_summary(period="today")
    week = get_sales_summary(period="week")
    total = get_sales_summary()
    available = count_accounts(status="available")
    sold = count_accounts(status="sold")
    pending = count_accounts(status="pending_payment")
    sellers = list_sellers()

    now = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"📊 Daily Sales Report — {now}",
        "",
        f"💰 Revenue today: ₹{today.get('total_revenue', 0):.0f}",
        f"📈 Sales today: {today.get('total_sales', 0)}",
        f"💳 Pending payments: {today.get('pending_count', 0)} (₹{today.get('pending_amount', 0):.0f})",
        f"📦 Inventory: 🟢{available} 🔴{sold} 🟡{pending}",
        "",
        "By seller:",
    ]
    for s in sellers:
        if s["sale_count"] > 0:
            lines.append(f"• {s['name']}: {s['sale_count']} sales, ₹{s['total_earnings']:.0f}")
    if not any(s["sale_count"] > 0 for s in sellers):
        lines.append("• No sales yet")
    return "\n".join(lines)


def _build_weekly_report():
    week = get_sales_summary(period="week")
    total = get_sales_summary()
    available = count_accounts(status="available")
    sold = count_accounts(status="sold")
    pending = count_accounts(status="pending_payment")
    sellers = list_sellers()

    now = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"📊 Weekly Sales Report — {now}",
        "",
        f"💰 Revenue this week: ₹{week.get('total_revenue', 0):.0f}",
        f"📈 Sales this week: {week.get('total_sales', 0)}",
        f"💳 Pending payments: {week.get('pending_count', 0)} (₹{week.get('pending_amount', 0):.0f})",
        f"📦 Inventory: 🟢{available} 🔴{sold} 🟡{pending}",
        f"💰 All-time revenue: ₹{total.get('total_revenue', 0):.0f}",
        "",
        "By seller:",
    ]
    for s in sellers:
        if s["sale_count"] > 0:
            lines.append(f"• {s['name']}: {s['sale_count']} sales, ₹{s['total_earnings']:.0f}")
    if not any(s["sale_count"] > 0 for s in sellers):
        lines.append("• No sales yet")
    return "\n".join(lines)


def _build_pending_payment_report():
    pending = get_sales(limit=50, status="pending")
    if not pending:
        return None
    total_pending = sum(s["price"] for s in pending)
    lines = [
        f"🟡 Pending Payment Reminder — {len(pending)} sales (₹{total_pending:.0f})",
        "",
    ]
    for s in pending:
        lines.append(
            f"• #{s['id']} | {s['buyer_name']} | ₹{s['price']:.0f} | {str(s['sold_at'])[:10]}"
        )
    lines.append("")
    lines.append("Use /markpaid to confirm payment.")
    return "\n".join(lines)


async def daily_report_job(context):
    try:
        report = _build_daily_report()
        await context.bot.send_message(chat_id=config.ADMIN_USER_ID, text=report, parse_mode="HTML")
        logger.info("Daily report sent.")
    except Exception as e:
        logger.error("Daily report failed: %s", e)


async def weekly_report_job(context):
    try:
        report = _build_weekly_report()
        await context.bot.send_message(chat_id=config.ADMIN_USER_ID, text=report, parse_mode="HTML")
        logger.info("Weekly report sent.")
    except Exception as e:
        logger.error("Weekly report failed: %s", e)


async def pending_payment_job(context):
    try:
        report = _build_pending_payment_report()
        if report:
            await context.bot.send_message(chat_id=config.ADMIN_USER_ID, text=report, parse_mode="HTML")
            logger.info("Pending payment notification sent.")
    except Exception as e:
        logger.error("Pending payment notification failed: %s", e)


def setup_scheduler(application):
    scheduler.add_job(
        daily_report_job,
        CronTrigger(
            hour=config.DAILY_REPORT_HOUR,
            minute=config.DAILY_REPORT_MINUTE,
            timezone=config.TIMEZONE,
        ),
        args=[application],
        id="daily_report",
        replace_existing=True,
    )

    day_map = {
        "monday": "mon", "tuesday": "tue", "wednesday": "wed",
        "thursday": "thu", "friday": "fri", "saturday": "sat", "sunday": "sun",
    }
    report_day = day_map.get(config.WEEKLY_REPORT_DAY, "mon")

    scheduler.add_job(
        weekly_report_job,
        CronTrigger(
            day_of_week=report_day,
            hour=config.DAILY_REPORT_HOUR,
            minute=config.DAILY_REPORT_MINUTE,
            timezone=config.TIMEZONE,
        ),
        args=[application],
        id="weekly_report",
        replace_existing=True,
    )

    scheduler.add_job(
        pending_payment_job,
        IntervalTrigger(hours=4),
        args=[application],
        id="pending_payment",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started.")
