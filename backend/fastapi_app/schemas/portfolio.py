from pydantic import BaseModel
from datetime import datetime
from typing import List


class PortfolioItem(BaseModel):
    symbol: str
    quantity: int
    purchase_price: float
    current_price: float
    current_value: float
    gain_loss: float


class PortfolioResponse(BaseModel):
    user_id: int
    portfolio: List[PortfolioItem]


class PortfolioHistoryResponse(BaseModel):
    timestamp: datetime
    portfolio_value: float
    volatility: float
    profit: float
    investment_value: float
    asset_value: float
    dividends: float
