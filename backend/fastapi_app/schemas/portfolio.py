from pydantic import BaseModel
from typing import List


class PortfolioItem(BaseModel):
    symbol: str
    quantity: float
    purchase_price: float
    current_price: float
    current_value: float
    gain_loss: float


class PortfolioResponse(BaseModel):
    user_id: int
    portfolio: List[PortfolioItem]