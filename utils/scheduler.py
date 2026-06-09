import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import config
from core.format import code
from database.sales import get_sales_summary, get_sales, count_sales
from database.accounts import count_accounts
from database.sellers import list_sellers

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone=config.TIMEZONE)


def _build_daily_report():
    try:
        today = get_sales_summary(period="today")
        available = count_accounts(status="available")
        sold = count_accounts(status="sold")
        pending = count_accounts(status="pending_payment")
        sellers = list_sellers()

        now = datetime.now().strftime("%Y-%m-%d")
        lines = [
            f"📊 <b>Daily Sales Report — {now}</b>",
            "",
            f"💰 Revenue today: {config.CURRENCY}{today.get('total_revenue', 0):.0f}",
            f"📈 Sales today: {today.get('total_sales', 0)}",
            f"💳 Pending payments: {today.get('pending_count', 0)} ({config.CURRENCY}{today.get('pending_amount', 0):.0f})",
            f"📦 Inventory: 🟢{available} 🔴{sold} 🟡{pending}",
            "",
            "<b>By seller:</b>",
        ]
        has_sales = False
        for s in sellers:
            if s.get("sale_count", 0) > 0:
                lines.append(f"• {s['name']}: {s['sale_count']} sales, {config.CURRENCY}{s['total_earnings']:.0f}")
                has_sales = True
        if not has_sales:
            lines.append("• No sales yet")
        return "\n".join(lines)
    except Exception as e:
        logger.error("Failed to build daily report: %s", e)
        return f"📊 Daily report failed to generate: {e}"


def _build_weekly_report():
    try:
        week = get_sales_summary(period="week")
        total = get_sales_summary()
        available = count_accounts(status="available")
        sold = count_accounts(status="sold")
        pending = count_accounts(status="pending_payment")
        sellers = list_sellers()

        now = datetime.now().strftime("%Y-%m-%d")
        lines = [
            f"📊 <b>Weekly Sales Report — {now}</b>",
            "",
            f"💰 Revenue this week: {config.CURRENCY}{week.get('total_revenue', 0):.0f}",
            f"📈 Sales this week: {week.get('total_sales', 0)}",
            f"💳 Pending payments: {week.get('pending_count', 0)} ({config.CURRENCY}{week.get('pending_amount', 0):.0f})",
            f"📦 Inventory: 🟢{available} 🔴{sold} 🟡{pending}",
            f"💰 All-time revenue: {config.CURRENCY}{total.get('total_revenue', 0):.0f}",
            "",
            "<b>By seller:</b>",
        ]
        has_sales = False
        for s in sellers:
            if s.get("sale_count", 0) > 0:
                lines.append(f"• {s['name']}: {s['sale_count']} sales, {config.CURRENCY}{s['total_earnings']:.0f}")
                has_sales = True
        if not has_sales:
            lines.append("• No sales yet")
        return "\n".join(lines)
    except Exception as e:
        logger.error("Failed to build weekly report: %s", e)
        return f"📊 Weekly report failed to generate: {e}"


def _build_pending_payment_report():
    try:
        pending = get_sales(limit=50, status="pending")
        if not pending:
            return None
        total_pending = sum(s.get("price", 0) for s in pending)
        lines = [
            f"🟡 <b>Pending Payment Reminder — {len(pending)} sales ({config.CURRENCY}{total_pending:.0f})</b>",
            "",
        ]
        for s in pending:
            sale_code = s.get("sale_code", f"#{s.get('id', '?')}")
            lines.append(
                f"• {code(sale_code)} | {code(s.get('buyer_name', '—'))} | "
                f"{config.CURRENCY}{s.get('price', 0):.0f} | {str(s.get('sold_at', ''))[:10]}"
            )
        lines.append("")
        lines.append("Use /markpaid to confirm payment.")
        return "\n".join(lines)
    except Exception as e:
        logger.error("Failed to build pending payment report: %s", e)
        return None


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

    if not scheduler.running:
        scheduler.start()
    logger.info("Scheduler started.")
