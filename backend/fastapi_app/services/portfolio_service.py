from datetime import datetime, timedelta
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, Depends
from sqlalchemy.orm import joinedload
from sqlalchemy.future import select
import yfinance as yf
import asyncio


from fastapi_app.services.stock_service import (
    get_latest_stock_prices,
    get_user_with_stocks,
)
from fastapi_app.schemas.portfolio import (
    PortfolioResponse,
    PortfolioItem,
    PortfolioHistoryResponse,
)
from fastapi_app.models.user import User, Stock, StockPrice, PortfolioHistory
from shared.logging_config import setup_logging
from fastapi_app.db.database import get_db


logger = setup_logging()


async def get_user_portfolio(
    current_user: User, db: AsyncSession = Depends(get_db)
) -> PortfolioResponse:
    try:
        user = await get_user_with_stocks(current_user.id, db)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        stock_symbols = [stock.symbol for stock in user.stocks]
        price_data = await get_latest_stock_prices(stock_symbols, db)

        portfolio = build_portfolio_response(user.stocks, price_data)
        return PortfolioResponse(user_id=user.id, portfolio=portfolio)
    except Exception as e:
        logger.error(f"Error in get_user_portfolio: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def get_portfolio_history(
    current_user: User, db: AsyncSession = Depends(get_db), days: int = 30
) -> List[PortfolioHistoryResponse]:
    try:
        start_date, end_date = get_date_range(days)
        history = await fetch_portfolio_history(
            current_user.id, start_date, end_date, db
        )

        return [build_portfolio_history_response(h) for h in history]
    except Exception as e:
        logger.error(f"Error in get_portfolio_history: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


def build_portfolio_response(stocks, price_data):
    portfolio = []
    for stock in stocks:
        latest_price = price_data.get(stock.symbol)
        if latest_price:
            current_value = round(stock.quantity * latest_price, 3)
            gain_loss = round(
                current_value - (stock.quantity * stock.purchase_price), 3
            )
            portfolio.append(
                PortfolioItem(
                    symbol=stock.symbol,
                    quantity=stock.quantity,
                    purchase_price=stock.purchase_price,
                    current_price=latest_price,
                    current_value=current_value,
                    gain_loss=gain_loss,
                )
            )
        else:
            logger.warning(f"No latest price found for stock: {stock.symbol}")
    return portfolio


def get_date_range(days: int):
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    return start_date, end_date


async def fetch_portfolio_history(
    user_id: int, start_date: datetime, end_date: datetime, db: AsyncSession
):
    stmt = (
        select(PortfolioHistory)
        .filter(
            PortfolioHistory.user_id == user_id,
            PortfolioHistory.timestamp >= start_date,
            PortfolioHistory.timestamp <= end_date,
        )
        .order_by(PortfolioHistory.timestamp.asc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


def build_portfolio_history_response(history):
    return PortfolioHistoryResponse(
        timestamp=history.timestamp,
        portfolio_value=history.portfolio_value,
        volatility=history.volatility,
        profit=history.profit,
        investment_value=history.investment_value,
        asset_value=history.asset_value,
        dividends=history.dividends,
    )


async def update_portfolio_history() -> None:
    logger.info("Starting portfolio history update")
    async for db in get_db():
        try:
            # Use distinct() instead of unique()
            stmt = select(User).options(joinedload(User.stocks)).distinct()
            result = await db.execute(stmt)
            users = result.scalars().all()
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
