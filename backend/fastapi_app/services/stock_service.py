from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi_app.models.user import Stock, StockPrice
from shared.logging_config import setup_logging
from fastapi_app.db.database import get_db
import yfinance as yf
import asyncio
import os

scheduler = BackgroundScheduler()
logger = setup_logging()

STOCK_PRICES_INTERVAL_UPDATES_SECONDS = int(
    os.getenv("STOCK_PRICES_INTERVAL_UPDATES_SECONDS", 60)
)


class StockService:
    def __init__(self, db):
        self.db = db

    async def update_stock_price(self, stock):
        logger.info(f"Updating price for {stock.symbol}")
        price = await self.fetch_stock_price(stock.symbol)
        if price is not None:
            self._save_stock_price(stock.symbol, price)

    async def fetch_stock_price(self, symbol):
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d")
            if not data.empty:
                price = round(float(data["Close"].iloc[-1]), 3)
                logger.info(f"Received price for {symbol}: {price}")
                return price
            else:
                logger.warning(f"No price data received for {symbol}")
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {str(e)}")
            return None

    def _save_stock_price(self, symbol, price):
        existing_price = (
            self.db.query(StockPrice).filter(StockPrice.symbol == symbol).first()
        )
        if existing_price:
            existing_price.price = price
            logger.info(f"Updated price for {symbol}")
        else:
            new_price = StockPrice(symbol=symbol, price=price)
            self.db.add(new_price)
            logger.info(f"Added new price entry for {symbol}")


async def update_stock_prices():
    logger.info("Starting stock price update")
    db = next(get_db())
    stock_service = StockService(db)
    try:
        stocks = db.query(Stock).all()
        logger.info(f"Found {len(stocks)} stocks to update")
        for stock in stocks:
            await stock_service.update_stock_price(stock)
        db.commit()
        logger.info("Stock price update completed successfully")
    except Exception as e:
        logger.error(f"Error in update_stock_prices: {str(e)}")
        db.rollback()
    finally:
        db.close()


def job_listener(event):
    from apscheduler.events import JobExecutionEvent, JobSubmissionEvent

    if isinstance(event, JobExecutionEvent):
        if event.exception:
            logger.error(f"Job {event.job_id} failed")
        else:
            logger.info(f"Job {event.job_id} completed successfully")
    elif isinstance(event, JobSubmissionEvent):
        logger.info(f"Job submitted: {event.job_id}")


scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
scheduler.add_job(
    id="update_stock_prices",
    func=lambda: asyncio.run(update_stock_prices()),
    trigger="interval",
    seconds=STOCK_PRICES_INTERVAL_UPDATES_SECONDS,
)
