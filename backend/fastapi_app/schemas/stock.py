from pydantic import BaseModel
from typing import List


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
