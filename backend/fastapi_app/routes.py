from fastapi import APIRouter, HTTPException, Depends
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from shared.database import get_db
from shared.models import User, Stock, StockPrice
from pydantic import BaseModel
import httpx
import os


load_dotenv()

router = APIRouter()

ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")
BASE_URL = "https://www.alphavantage.co/query"


class UserCreate(BaseModel):
    username: str
    email: str


class StockCreate(BaseModel):
    symbol: str
    quantity: float
    purchase_price: float


@router.post("/users/", response_model=UserCreate)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(username=user.username, email=user.email)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/users/{user_id}/stocks/", response_model=StockCreate)
def add_stock(user_id: int, stock: StockCreate, db: Session = Depends(get_db)):
    db_stock = Stock(**stock.dict(), user_id=user_id)
    db.add(db_stock)
    db.commit()
    db.refresh(db_stock)
    return db_stock


@router.get("/users/{user_id}/portfolio")
def get_user_portfolio(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    portfolio = []
    for stock in user.stocks:
        latest_price = (
            db.query(StockPrice)
            .filter(StockPrice.symbol == stock.symbol)
            .order_by(StockPrice.timestamp.desc())
            .first()
        )
        if latest_price:
            current_value = stock.quantity * latest_price.price
            gain_loss = current_value - (stock.quantity * stock.purchase_price)
            portfolio.append(
                {
                    "symbol": stock.symbol,
                    "quantity": stock.quantity,
                    "purchase_price": stock.purchase_price,
                    "current_price": latest_price.price,
                    "current_value": current_value,
                    "gain_loss": gain_loss,
                }
            )

    return {"portfolio": portfolio}


@router.get("/stocks/{symbol}")
async def get_stock_price(symbol: str):
    if ALPHAVANTAGE_API_KEY is None:
        raise HTTPException(status_code=500, detail="API key is not set")

    url = f"{BASE_URL}?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=1min&apikey={ALPHAVANTAGE_API_KEY}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail="Error fetching data from Alpha Vantage",
            )
        data = response.json()
    try:
        latest_time = next(iter(data["Time Series (1min)"]))
        latest_data = data["Time Series (1min)"][latest_time]
        price = latest_data["1. open"]
    except KeyError:
        raise HTTPException(status_code=404, detail="Stock symbol not found")

    return {"symbol": symbol, "price": price}
