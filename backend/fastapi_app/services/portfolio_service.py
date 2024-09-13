from datetime import datetime, timedelta
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
from fastapi import HTTPException


from fastapi_app.schemas.portfolio import (
    PortfolioResponse,
    PortfolioItem,
    PortfolioHistoryResponse,
)
from fastapi_app.services.stock_service import StockService
from fastapi_app.models.user import User, PortfolioHistory
from shared.logging_config import setup_logging


logger = setup_logging()


class PortfolioService:
    def __init__(self, stock_service: StockService):
        self.stock_service = stock_service

    async def get_user_portfolio(
        self, current_user: User, db: AsyncSession
    ) -> PortfolioResponse:
        try:
            user = await self.stock_service.get_user_with_stocks(current_user.id, db)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            stock_symbols = [stock.symbol for stock in user.stocks]
            price_data = await self.stock_service.get_latest_stock_prices(
                stock_symbols, db
            )

            portfolio = self._build_portfolio_response(user.stocks, price_data)
            return PortfolioResponse(user_id=user.id, portfolio=portfolio)
        except Exception as e:
            logger.error(f"Error in get_user_portfolio: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def get_portfolio_history(
        self, current_user: User, db: AsyncSession, days: int = 30
    ) -> List[PortfolioHistoryResponse]:
        try:
            start_date, end_date = self._get_date_range(days)
            history = await self._fetch_portfolio_history(
                current_user.id, start_date, end_date, db
            )

            return [self._build_portfolio_history_response(h) for h in history]
        except Exception as e:
            logger.error(f"Error in get_portfolio_history: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def update_portfolio_history(self, db: AsyncSession) -> None:
        logger.info("Starting portfolio history update")
        try:
            users = await self._get_users_with_stocks(db)
            logger.info(f"Updating portfolio history for {len(users)} users")

            for user in users:
                await self._update_user_portfolio_history(user, db)

            await db.commit()
            logger.info("Portfolio history update completed successfully")
        except Exception as e:
            logger.error(f"Error during portfolio history update: {str(e)}")
            await db.rollback()

    @staticmethod
    def _build_portfolio_response(stocks, price_data):
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

    @staticmethod
    def _get_date_range(days: int):
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        return start_date, end_date

    @staticmethod
    async def _fetch_portfolio_history(
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

    @staticmethod
    def _build_portfolio_history_response(history):
        return PortfolioHistoryResponse(
            timestamp=history.timestamp,
            portfolio_value=history.portfolio_value,
            volatility=history.volatility,
            profit=history.profit,
            investment_value=history.investment_value,
            asset_value=history.asset_value,
            dividends=history.dividends,
        )

    @staticmethod
    async def _get_users_with_stocks(db: AsyncSession):
        stmt = select(User).options(selectinload(User.stocks)).distinct()
        result = await db.execute(stmt)
        return result.scalars().all()

    async def _update_user_portfolio_history(self, user: User, db: AsyncSession):
        try:
            portfolio_items = await self.stock_service.get_user_portfolio_items(
                user.id, db
            )

            if not portfolio_items:
                logger.warning(f"No portfolio items found for user {user.id}")
                return

            portfolio_value = sum(
                stock.quantity * price.price
                for stock, price in portfolio_items
                if price
            )
            investment_value = sum(
                stock.quantity * stock.purchase_price for stock, _ in portfolio_items
            )
            dividends = await self.stock_service.calculate_total_dividends(user)
            volatility = await self.stock_service.calculate_portfolio_volatility(
                portfolio_items
            )

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
