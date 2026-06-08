import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import config
from database.sales import get_sales_summary, count_sales
from database.accounts import count_accounts
from database.sellers import list_sellers

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone=config.TIMEZONE)


def _build_daily_report():
    today = get_sales_summary(period="today")
    week = get_sales_summary(period="week")
    total = get_sales_summary()
    available = count_accounts(status="active")
    sold = count_accounts(used=True)
    sellers = list_sellers()

    now = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"📊 Daily Sales Report — {now}",
        "",
        f"💰 Revenue today: ₹{today['total_revenue']:.0f}",
        f"📈 Sales today: {today['total_sales']}",
        f"💳 Pending payments: {today['pending_count']} (₹{today['pending_amount']:.0f})",
        f"📦 Total inventory: {available} available, {sold} sold",
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
    available = count_accounts(status="active")
    sold = count_accounts(used=True)
    sellers = list_sellers()

    now = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"📊 Weekly Sales Report — {now}",
        "",
        f"💰 Revenue this week: ₹{week['total_revenue']:.0f}",
        f"📈 Sales this week: {week['total_sales']}",
        f"💳 Pending payments: {week['pending_count']} (₹{week['pending_amount']:.0f})",
        f"📦 Total inventory: {available} available, {sold} sold",
        f"💰 All-time revenue: ₹{total['total_revenue']:.0f}",
        "",
        "By seller:",
    ]
    for s in sellers:
        if s["sale_count"] > 0:
            lines.append(f"• {s['name']}: {s['sale_count']} sales, ₹{s['total_earnings']:.0f}")
    if not any(s["sale_count"] > 0 for s in sellers):
        lines.append("• No sales yet")
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

    scheduler.start()
    logger.info("Scheduler started.")
