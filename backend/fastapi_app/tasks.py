from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from apscheduler.schedulers.background import BackgroundScheduler
from shared.logging_config import setup_logging
from shared.models import Stock, StockPrice
from shared.database import get_db
import yfinance as yf
import asyncio

scheduler = BackgroundScheduler()

logger = setup_logging()


async def update_stock_prices():
    logger.info("Starting stock price update")
    db = next(get_db())
    try:
        stocks = db.query(Stock).all()
        logger.info(f"Found {len(stocks)} stocks to update")

        for stock in stocks:
            logger.info(f"Updating price for {stock.symbol}")
            try:
                ticker = yf.Ticker(stock.symbol)
                data = ticker.history(period="1d")
                if not data.empty:
                    price = round(float(data["Close"].iloc[-1]), 3)
                    logger.info(f"Received price for {stock.symbol}: {price}")

                    existing_price = (
                        db.query(StockPrice)
                        .filter(StockPrice.symbol == stock.symbol)
                        .first()
                    )

                    if existing_price:
                        existing_price.price = price
                        logger.info(f"Updated price for {stock.symbol}")
                    else:
                        new_price = StockPrice(symbol=stock.symbol, price=price)
                        db.add(new_price)
                        logger.info(f"Added new price entry for {stock.symbol}")
                else:
                    logger.warning(f"No price data received for {stock.symbol}")
            except Exception as e:
                logger.error(f"Error updating price for {stock.symbol}: {str(e)}")

        db.commit()
        logger.info("Stock price update completed successfully")
    except Exception as e:
        logger.error(f"Error in update_stock_prices: {str(e)}")
        db.rollback()
    finally:
        db.close()


def job_listener(event):
    if event.exception:
        logger.error(f"Job failed: {event.job_id}")
    else:
        logger.info(f"Job completed successfully: {event.job_id}")


scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
scheduler.add_job(
    id="update_stock_prices",
    func=lambda: asyncio.run(update_stock_prices()),
    trigger="interval",
    seconds=15,
)
scheduler.start()
