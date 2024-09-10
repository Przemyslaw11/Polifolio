from typing import Optional, List, Dict, Any
from datetime import datetime
import os

from apscheduler.events import JobExecutionEvent, JobSubmissionEvent
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import joinedload
from sqlalchemy.future import select
from sqlalchemy.orm import Session
from fastapi import HTTPException
import yfinance as yf
import asyncio

from fastapi_app.models.user import User, Stock, StockPrice, PortfolioHistory
from fastapi_app.schemas.stock import StockAnalysisResponse
from shared.logging_config import setup_logging
from fastapi_app.db.database import get_db

scheduler = AsyncIOScheduler()
logger = setup_logging()

STOCK_PRICES_INTERVAL_UPDATES_SECONDS = int(
    os.getenv("STOCK_PRICES_INTERVAL_UPDATES_SECONDS", 60)
)
PORTFOLIO_HISTORY_UPDATE_INTERVAL_SECONDS = int(
    os.getenv("PORTFOLIO_HISTORY_UPDATE_INTERVAL_SECONDS", 3600)
)


class StockService:
    def __init__(self, db: Session):
        self.db = db
        self.updated_symbols = set()

    async def update_stock_price(self, stock: Stock) -> None:
        if stock.symbol in self.updated_symbols:
            logger.info(
                f"Skipping {stock.symbol} as it was already updated in current job run"
            )
            return

        logger.info(f"Updating price for {stock.symbol}")
        price = await self.fetch_stock_price(stock.symbol)
        if price is not None:
            await self._save_stock_price(stock.symbol, price)
            self.updated_symbols.add(stock.symbol)

    @staticmethod
    async def fetch_stock_price(symbol: str) -> Optional[float]:
        try:
            ticker = yf.Ticker(symbol)
            data = await asyncio.to_thread(ticker.history, period="1d")
            if not data.empty:
                price = round(float(data["Close"].iloc[-1]), 3)
                logger.info(f"Received price for {symbol}: {price}")
                return price
            else:
                logger.warning(f"No price data received for {symbol}")
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {str(e)}")
        return None

    async def _save_stock_price(self, symbol: str, price: float) -> None:
        try:
            stmt = select(StockPrice).filter(StockPrice.symbol == symbol)
            result = await self.db.execute(stmt)
            existing_price = result.scalar_one_or_none()

            if existing_price:
                existing_price.price = price
                existing_price.timestamp = datetime.utcnow()
                logger.info(f"Updated price for {symbol}")
            else:
                new_price = StockPrice(symbol=symbol, price=price)
                self.db.add(new_price)
                logger.info(f"Added new price entry for {symbol}")

            await self.db.commit()
        except Exception as e:
            logger.error(f"Error saving stock price for {symbol}: {str(e)}")
            await self.db.rollback()


async def update_stock_prices():
    logger.info("Starting stock price update")
    async for db in get_db():
        stock_service = StockService(db=db)
        try:
            stmt = select(Stock.symbol).distinct()
            result = await db.execute(stmt)
            stocks = result.scalars().all()
            logger.info(f"Found {len(stocks)} unique stocks to update")
            await asyncio.gather(
                *[
                    stock_service.update_stock_price(Stock(symbol=symbol))
                    for symbol in stocks
                ]
            )
            logger.info("Stock price update completed successfully")
        except Exception as e:
            logger.error(f"Error during stock price update: {str(e)}")
        finally:
            await db.close()


def calculate_portfolio_volatility(portfolio_items: List[tuple]) -> float:
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

    return sum(weighted_volatilities) if weighted_volatilities else 0.0


async def calculate_total_dividends(user: User) -> float:
    total_dividends = 0
    for stock in user.stocks:
        try:
            ticker = yf.Ticker(stock.symbol)
            dividends = await asyncio.to_thread(lambda: ticker.dividends)
            if not dividends.empty:
                total_dividends += dividends.sum() * stock.quantity
            else:
                logger.info(f"No dividend data available for {stock.symbol}")
        except Exception as e:
            logger.error(f"Error fetching dividend data for {stock.symbol}: {str(e)}")
    return total_dividends


async def update_portfolio_history() -> None:
    logger.info("Starting portfolio history update")
    async for db in get_db():
        try:
            stmt = select(User).options(joinedload(User.stocks)).unique()
            result = await db.execute(stmt)
            users = result.scalars().unique().all()
            logger.info(f"Updating portfolio history for {len(users)} users")

            for user in users:
                try:
                    stmt = (
                        select(Stock, StockPrice)
                        .outerjoin(StockPrice, Stock.symbol == StockPrice.symbol)
                        .filter(Stock.user_id == user.id)
                    )
                    result = await db.execute(stmt)
                    portfolio_items = result.all()

                    if not portfolio_items:
                        logger.warning(f"No portfolio items found for user {user.id}")
                        continue

                    portfolio_value = sum(
                        stock.quantity * price.price
                        for stock, price in portfolio_items
                        if price
                    )
                    investment_value = sum(
                        stock.quantity * stock.purchase_price
                        for stock, _ in portfolio_items
                    )
                    dividends = await calculate_total_dividends(user)
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

                    db.add(history_entry)
                    logger.info(f"Added portfolio history entry for user {user.id}")

                except Exception as e:
                    logger.error(
                        f"Error updating portfolio history for user {user.id}: {str(e)}"
                    )

            await db.commit()
            logger.info("Portfolio history update completed successfully")

        except Exception as e:
            logger.error(f"Error during portfolio history update: {str(e)}")
            await db.rollback()
        finally:
            await db.close()


async def get_stock_data(symbol: str) -> Dict[str, Any]:
    try:
        ticker = yf.Ticker(symbol)
        data = await asyncio.to_thread(ticker.history, period="1mo")
        if data.empty:
            raise HTTPException(status_code=404, detail="Stock symbol not found")
        latest_price = float(round(data["Close"].iloc[-1], 3))
        return {"symbol": symbol, "price": latest_price}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching stock data: {str(e)}"
        )


async def analyze_stock(
    symbol: str, quantity: float, purchase_price: float
) -> StockAnalysisResponse:
    try:
        ticker = yf.Ticker(symbol)
        data = await asyncio.to_thread(ticker.history, period="1y")

        if data.empty:
            raise HTTPException(status_code=404, detail="Stock symbol not found")

        data = data.reset_index()

        data["Returns"] = data["Close"].pct_change()
        data["Cumulative Returns"] = (1 + data["Returns"]).cumprod()

        initial_investment = quantity * purchase_price
        data["Portfolio Value"] = data["Cumulative Returns"] * initial_investment

        dividends_data = ticker.dividends.reset_index()
        dividends = (
            dividends_data.to_dict(orient="records") if not dividends_data.empty else []
        )

        volatility = data["Returns"].std() * 252**0.5

        return StockAnalysisResponse(
            historical_data=data.to_dict(orient="records"),
            portfolio_value=data[["Date", "Portfolio Value"]].to_dict(orient="records"),
            volatility=volatility,
            profit_over_time=data[["Date", "Cumulative Returns"]].to_dict(
                orient="records"
            ),
            investment_value_over_time=data[["Date", "Close"]].to_dict(
                orient="records"
            ),
            asset_value_over_time=data[["Date", "Portfolio Value"]].to_dict(
                orient="records"
            ),
            dividends=dividends,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching stock analysis data: {str(e)}"
        )


async def job_listener(event):
    if isinstance(event, JobExecutionEvent):
        if event.exception:
            logger.error(f"Job {event.job_id} failed")
        else:
            logger.info(f"Job {event.job_id} completed successfully")
    elif isinstance(event, JobSubmissionEvent):
        logger.info(f"Job submitted: {event.job_id}")


scheduler.add_listener(job_listener)

scheduler.add_job(
    update_stock_prices,
    trigger=IntervalTrigger(seconds=STOCK_PRICES_INTERVAL_UPDATES_SECONDS),
    id="update_stock_prices",
    max_instances=1,
)

scheduler.add_job(
    update_portfolio_history,
    trigger=IntervalTrigger(seconds=PORTFOLIO_HISTORY_UPDATE_INTERVAL_SECONDS),
    id="update_portfolio_history",
    max_instances=1,
)
