from typing import Optional, List, Dict, Any
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.future import select
from fastapi import HTTPException
from sqlalchemy import func
import yfinance as yf
import asyncio

from fastapi_app.models.user import User, Stock, StockPrice
from fastapi_app.schemas.stock import StockAnalysisResponse
from fastapi_app.db.database import AsyncSessionLocal
from shared.logging_config import setup_logging

scheduler = AsyncIOScheduler()
logger = setup_logging()


class StockService:
    def __init__(self):
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
        async with AsyncSessionLocal() as db:
            try:
                stmt = select(StockPrice).filter(StockPrice.symbol == symbol)
                result = await db.execute(stmt)
                existing_price = result.scalar_one_or_none()

                if existing_price:
                    existing_price.price = price
                    existing_price.timestamp = datetime.utcnow()
                    logger.info(f"Updated price for {symbol}")
                else:
                    new_price = StockPrice(symbol=symbol, price=price)
                    db.add(new_price)
                    logger.info(f"Added new price entry for {symbol}")

                await db.commit()
            except Exception as e:
                logger.error(f"Error saving stock price for {symbol}: {str(e)}")
                await db.rollback()


async def update_stock_prices():
    logger.info("Starting stock price update")
    stock_service = StockService()
    async with AsyncSessionLocal() as db:
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


async def get_user_with_stocks(user_id: int, db: AsyncSession):
    stmt = select(User).options(joinedload(User.stocks)).filter(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalars().unique().one_or_none()


async def get_latest_stock_prices(stock_symbols: List[str], db: AsyncSession):
    subquery = (
        select(StockPrice.symbol, func.max(StockPrice.timestamp).label("max_timestamp"))
        .filter(StockPrice.symbol.in_(stock_symbols))
        .group_by(StockPrice.symbol)
        .subquery()
    )

    stmt = select(StockPrice).join(
        subquery,
        (StockPrice.symbol == subquery.c.symbol)
        & (StockPrice.timestamp == subquery.c.max_timestamp),
    )
    result = await db.execute(stmt)
    return {row.symbol: row.price for row in result.scalars().all()}
