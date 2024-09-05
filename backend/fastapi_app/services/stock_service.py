from apscheduler.events import JobExecutionEvent, JobSubmissionEvent
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi_app.models.user import User, Stock, StockPrice, PortfolioHistory
from shared.logging_config import setup_logging
from fastapi_app.db.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy.orm import aliased
from sqlalchemy import func
from typing import Optional
import yfinance as yf
import asyncio
import os

scheduler = BackgroundScheduler()
logger = setup_logging()

STOCK_PRICES_INTERVAL_UPDATES_SECONDS = int(
    os.getenv("STOCK_PRICES_INTERVAL_UPDATES_SECONDS", 60)
)

PORTFOLIO_HISTORY_UPDATE_INTERVAL_SECONDS = int(
    os.getenv("PORTFOLIO_HISTORY_UPDATE_INTERVAL_SECONDS", 3600)
)


class StockService:
    def __init__(self, db: Session, updated_symbols: set):
        """
        Initialize the StockService with a database session and a set to track updated symbols.
        args:
            - db: The database session
            - updated_symbols: A set to track which stock symbols have been updated
        """
        self.db = db
        self.updated_symbols = updated_symbols

    async def update_stock_price(self, stock: Stock) -> None:
        """
        Update the price of a given stock, but only if it hasn't been updated already in current job run.
        args:
            - stock: The Stock object to update
        return: None
        """
        if stock.symbol in self.updated_symbols:
            logger.info(
                f"Skipping {stock.symbol} as it was already updated in current job run"
            )
            return

        logger.info(f"Updating price for {stock.symbol}")
        price = await self.fetch_stock_price(stock.symbol)
        if price is not None:
            self._save_stock_price(stock.symbol, price)
            self.updated_symbols.add(stock.symbol)

    async def fetch_stock_price(self, symbol: str) -> Optional[float]:
        """
        Fetch the current price of a stock from Yahoo Finance.
        args:
            - symbol: The stock symbol to fetch the price for
        return: The current price of the stock, or None if an error occurred
        """
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

    def _save_stock_price(self, symbol: str, price: float) -> None:
        """
        Save or update the price of a stock in the database.
        args:
            - symbol: The stock symbol
            - price: The current price of the stock
        return: None
        """
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


async def update_stock_prices() -> None:
    logger.info("Starting stock price update")
    db = next(get_db())

    updated_symbols = set()
    stock_service = StockService(db=db, updated_symbols=updated_symbols)

    try:
        stocks = db.query(Stock).distinct(Stock.symbol).all()
        logger.info(f"Found {len(stocks)} unique stocks to update")

        for stock in stocks:
            try:
                await stock_service.update_stock_price(stock)
                logger.info(f"Updated price for {stock.symbol}")
            except Exception as e:
                logger.error(f"Error updating price for {stock.symbol}: {str(e)}")

        db.commit()
        logger.info("Stock price update completed successfully")

    except Exception as e:
        logger.error(f"Error during stock price update: {str(e)}")
        db.rollback()


def calculate_portfolio_volatility(portfolio_items):
    if not portfolio_items:
        logger.warning("No portfolio items provided for volatility calculation")
        return 0.0

    total_value = sum(
        (item[0].quantity * item[1].price)
        for item in portfolio_items
        if item[1] is not None
    )
    if total_value == 0:
        logger.warning("Total portfolio value is zero")
        return 0.0

    weighted_volatilities = []

    for stock, price_entry in portfolio_items:
        if price_entry is None:
            logger.warning(f"No price data available for {stock.symbol}")
            continue

        try:
            ticker = yf.Ticker(stock.symbol)
            stock_data = ticker.history(period="1y")
            if stock_data.empty:
                logger.warning(f"No historical data available for {stock.symbol}")
                continue

            returns = stock_data["Close"].pct_change().dropna()
            volatility = returns.std() * (252**0.5)
            weight = (stock.quantity * price_entry.price) / total_value
            weighted_volatilities.append(weight * volatility)
        except Exception as e:
            logger.error(f"Error calculating volatility for {stock.symbol}: {str(e)}")

    if not weighted_volatilities:
        logger.warning("No valid volatilities calculated")
        return 0.0

    return sum(weighted_volatilities)


def calculate_total_dividends(user):
    total_dividends = 0
    for stock in user.stocks:
        try:
            ticker = yf.Ticker(stock.symbol)
            dividends = ticker.dividends
            if not dividends.empty:
                total_dividends += dividends.sum() * stock.quantity
            else:
                logger.info(f"No dividend data available for {stock.symbol}")
        except Exception as e:
            logger.error(f"Error fetching dividend data for {stock.symbol}: {str(e)}")
    return total_dividends


async def update_portfolio_history() -> None:
    logger.info("Starting portfolio history update")
    db = next(get_db())

    try:
        users = db.query(User).all()
        logger.info(f"Updating portfolio history for {len(users)} users")

        for user in users:
            try:
                portfolio_items = (
                    db.query(Stock, StockPrice)
                    .outerjoin(StockPrice, Stock.symbol == StockPrice.symbol)
                    .filter(Stock.user_id == user.id)
                    .all()
                )

                if not portfolio_items:
                    logger.warning(f"No portfolio items found for user {user.id}")
                    continue

                portfolio_value = 0.0
                investment_value = 0.0
                dividends = calculate_total_dividends(user)

                for stock, price_entry in portfolio_items:
                    if price_entry:
                        current_price = price_entry.price
                        quantity = stock.quantity

                        logger.debug(
                            f"Stock: {stock.symbol}, Quantity: {quantity}, Current Price: {current_price}"
                        )

                        if quantity is None or quantity < 0:
                            logger.error(
                                f"Invalid quantity for stock {stock.symbol}: {quantity}"
                            )
                            continue

                        current_value = float(quantity) * current_price
                        portfolio_value += current_value
                        investment_value += float(quantity) * stock.purchase_price

                        logger.debug(
                            f"Current Value: {current_value}, Portfolio Value: {portfolio_value}, Investment Value: {investment_value}"
                        )

                    else:
                        logger.warning(f"No price data found for stock {stock.symbol}")
                        continue

                logger.debug(
                    f"User {user.id} - Portfolio Value: {portfolio_value}, Investment Value: {investment_value}, Dividends: {dividends}"
                )

                volatility = calculate_portfolio_volatility(portfolio_items)

                logger.info(
                    f"Calculated values for user {user.id}: "
                    f"portfolio_value={portfolio_value:.2f}, "
                    f"volatility={volatility:.2f}, "
                    f"profit={portfolio_value - investment_value:.2f}, "
                    f"investment_value={investment_value:.2f}, "
                    f"dividends={dividends:.2f}"
                )

                history_entry = PortfolioHistory(
                    user_id=user.id,
                    portfolio_value=round(float(portfolio_value), 2),
                    volatility=round(float(volatility), 2),
                    profit=round(float(portfolio_value - investment_value), 2),
                    investment_value=round(float(investment_value), 2),
                    asset_value=round(float(portfolio_value), 2),
                    dividends=round(float(dividends), 2),
                )

                logger.debug(f"Adding PortfolioHistory entry: {history_entry}")

                db.add(history_entry)
                logger.info(f"Added portfolio history entry for user {user.id}")

            except Exception as e:
                logger.error(
                    f"Error updating portfolio history for user {user.id}: {str(e)}"
                )

        db.commit()
        logger.info("Portfolio history update completed successfully")

    except Exception as e:
        logger.error(f"Error during portfolio history update: {str(e)}")
        db.rollback()


def job_listener(event) -> None:
    """
    Listen for job execution events and log their status.
    args:
        - event: The job execution event
    return: None
    """
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

scheduler.add_job(
    id="update_portfolio_history",
    func=lambda: asyncio.run(update_portfolio_history()),
    trigger="interval",
    seconds=PORTFOLIO_HISTORY_UPDATE_INTERVAL_SECONDS,
)
