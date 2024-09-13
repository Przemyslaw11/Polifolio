from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from apscheduler.triggers.interval import IntervalTrigger

from services.portfolio_service import PortfolioService
from fastapi_app.db.database import AsyncSessionLocal
from services.stock_service import StockService
from shared.logging_config import setup_logging
from shared.config import settings

logger = setup_logging()
scheduler = AsyncIOScheduler()

stock_service = StockService()
portfolio_service = PortfolioService(stock_service)


def job_listener(event):
    if event.code == EVENT_JOB_EXECUTED:
        logger.info(f"Job {event.job_id} executed successfully")
    elif event.code == EVENT_JOB_ERROR:
        logger.error(f"Job {event.job_id} failed with exception: {event.exception}")


async def update_stock_prices_job():
    await stock_service.update_stock_prices()


async def update_portfolio_history_job():
    async with AsyncSessionLocal() as db:
        await portfolio_service.update_portfolio_history(db)


def configure_scheduler():
    """Configure the jobs and start the scheduler."""
    scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    scheduler.add_job(
        update_stock_prices_job,
        trigger=IntervalTrigger(seconds=settings.STOCK_PRICES_INTERVAL_UPDATES_SECONDS),
        id="update_stock_prices",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=settings.MISFIRE_GRACE_TIME_SECONDS,
    )

    scheduler.add_job(
        update_portfolio_history_job,
        trigger=IntervalTrigger(
            seconds=settings.PORTFOLIO_HISTORY_UPDATE_INTERVAL_SECONDS
        ),
        id="update_portfolio_history",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=settings.MISFIRE_GRACE_TIME_SECONDS,
    )

    scheduler.start()


def start_scheduler():
    configure_scheduler()
