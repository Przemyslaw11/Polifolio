from datetime import datetime, timedelta
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, Depends
from sqlalchemy.orm import joinedload
from sqlalchemy.future import select
from sqlalchemy import func

from fastapi_app.models.user import User, StockPrice, PortfolioHistory
from fastapi_app.schemas.portfolio import (
    PortfolioResponse,
    PortfolioItem,
    PortfolioHistoryResponse,
)
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
