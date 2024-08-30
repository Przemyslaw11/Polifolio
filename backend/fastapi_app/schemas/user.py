from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int


class TokenData(BaseModel):
    username: str | None = None


class StockCreate(BaseModel):
    symbol: str
    quantity: float
    purchase_price: float
