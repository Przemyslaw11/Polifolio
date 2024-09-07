from typing import List, Dict

from pydantic import BaseModel


class StockResponse(BaseModel):
    symbol: str
    price: float


class UserStocksResponse(BaseModel):
    user_id: int
    stocks: List[StockResponse]


class StockCreate(BaseModel):
    symbol: str
    quantity: int
    purchase_price: float


class StockAnalysisResponse(BaseModel):
    historical_data: List[Dict]
    portfolio_value: List[Dict]
    volatility: float
    profit_over_time: List[Dict]
    investment_value_over_time: List[Dict]
    asset_value_over_time: List[Dict]
    dividends: List[Dict]
