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
        stmt = (
            select(User)
            .options(joinedload(User.stocks))
            .filter(User.id == current_user.id)
        )
        result = await db.execute(stmt)
        user = result.scalars().unique().one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        stock_symbols = [stock.symbol for stock in user.stocks]

        subquery = (
            select(
                StockPrice.symbol, func.max(StockPrice.timestamp).label("max_timestamp")
            )
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
        price_data = {row.symbol: row.price for row in result.scalars().all()}

        portfolio = []
        for stock in user.stocks:
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

        return PortfolioResponse(user_id=user.id, portfolio=portfolio)
    except Exception as e:
        logger.error(f"Error in get_user_portfolio: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def get_portfolio_history(
    current_user: User, db: AsyncSession = Depends(get_db), days: int = 30
) -> List[PortfolioHistoryResponse]:
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        stmt = (
            select(PortfolioHistory)
            .distinct()
            .filter(
                PortfolioHistory.user_id == current_user.id,
                PortfolioHistory.timestamp >= start_date,
                PortfolioHistory.timestamp <= end_date,
            )
            .order_by(PortfolioHistory.timestamp.asc())
        )
        result = await db.execute(stmt)
        history = result.scalars().all()

        return [
            PortfolioHistoryResponse(
                timestamp=h.timestamp,
                portfolio_value=h.portfolio_value,
                volatility=h.volatility,
                profit=h.profit,
                investment_value=h.investment_value,
                asset_value=h.asset_value,
                dividends=h.dividends,
            )
            for h in history
        ]
    except Exception as e:
        logger.error(f"Error in get_portfolio_history: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
