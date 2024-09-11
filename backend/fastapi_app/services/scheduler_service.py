import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from apscheduler.triggers.interval import IntervalTrigger

from services.portfolio_service import update_portfolio_history
from services.stock_service import update_stock_prices
from shared.logging_config import setup_logging

logger = setup_logging()
scheduler = AsyncIOScheduler()

STOCK_PRICES_INTERVAL_UPDATES_SECONDS = int(
    os.getenv("STOCK_PRICES_INTERVAL_UPDATES_SECONDS", 60)
)
PORTFOLIO_HISTORY_UPDATE_INTERVAL_SECONDS = int(
    os.getenv("PORTFOLIO_HISTORY_UPDATE_INTERVAL_SECONDS", 3600)
)

MISFIRE_GRACE_TIME_SECONDS = (
    STOCK_PRICES_INTERVAL_UPDATES_SECONDS + STOCK_PRICES_INTERVAL_UPDATES_SECONDS
) // 2


def job_listener(event):
    if event.code == EVENT_JOB_EXECUTED:
        logger.info(f"Job {event.job_id} executed successfully")
    elif event.code == EVENT_JOB_ERROR:
        logger.error(f"Job {event.job_id} failed with exception: {event.exception}")


def configure_scheduler():
    """Configure the jobs and start the scheduler."""
    scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    scheduler.add_job(
        update_stock_prices,
        trigger=IntervalTrigger(seconds=STOCK_PRICES_INTERVAL_UPDATES_SECONDS),
        id="update_stock_prices",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=MISFIRE_GRACE_TIME_SECONDS,
    )

    scheduler.add_job(
        update_portfolio_history,
        trigger=IntervalTrigger(seconds=PORTFOLIO_HISTORY_UPDATE_INTERVAL_SECONDS),
        id="update_portfolio_history",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=MISFIRE_GRACE_TIME_SECONDS,
    )

    scheduler.start()


def start_scheduler():
    configure_scheduler()
