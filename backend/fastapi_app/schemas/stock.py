from pydantic import BaseModel
from typing import List, Dict


class StockResponse(BaseModel):
    symbol: str
    price: float


class UserStocksResponse(BaseModel):
    user_id: int
    stocks: List[StockResponse]


class StockCreate(BaseModel):
    symbol: str
    quantity: float
    purchase_price: float


class StockAnalysisResponse(BaseModel):
    historical_data: List[Dict]
    portfolio_value: List[Dict]
    volatility: float
    profit_over_time: List[Dict]
    investment_value_over_time: List[Dict]
    asset_value_over_time: List[Dict]
    dividends: List[Dict]
