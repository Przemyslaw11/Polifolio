from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import APIRouter, HTTPException, Depends, status
from shared.models import User, Stock, StockPrice
from shared.logging_config import setup_logging
from passlib.context import CryptContext
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from shared.database import get_db
from pydantic import BaseModel
from jose import JWTError, jwt
from dotenv import load_dotenv
import httpx
import os

load_dotenv()

logger = setup_logging()
router = APIRouter()

ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")
BASE_URL = "https://www.alphavantage.co/query"

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


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


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def authenticate_user(db: Session, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        logger.warning(f"User not found: {username}")
        return False
    if not verify_password(password, user.hashed_password):
        logger.warning(f"Incorrect password for user: {username}")
        return False
    logger.info(f"User authenticated: {username}")
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    return user


@router.post("/users/", response_model=UserCreate)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=get_password_hash(user.password),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return UserCreate(username=db_user.username, email=db_user.email, password="")


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "user_id": user.id}


@router.post("/users/{user_id}/stocks/", response_model=StockCreate)
def add_stock(
    user_id: int,
    stock: StockCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to add stocks for this user"
        )
    db_stock = Stock(**stock.dict(), user_id=user_id)
    db.add(db_stock)
    db.commit()
    db.refresh(db_stock)
    return db_stock


@router.get("/debug/user_stocks/{user_id}")
def debug_user_stocks(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"error": "User not found"}

    stocks = [
        {
            "symbol": stock.symbol,
            "quantity": stock.quantity,
            "purchase_price": stock.purchase_price,
        }
        for stock in user.stocks
    ]
    return {"user_id": user_id, "stocks": stocks}


@router.get("/portfolio")
def get_user_portfolio(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logger.info(f"Fetching portfolio for user: {current_user.username}")
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        logger.error(f"User not found: {current_user.username}")
        raise HTTPException(status_code=404, detail="User not found")

    portfolio = []
    logger.info(f"Number of stocks for user {user.username}: {len(user.stocks)}")
    for stock in user.stocks:
        logger.info(f"Processing stock: {stock.symbol}")
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
        else:
            logger.warning(f"No latest price found for stock: {stock.symbol}")

    logger.info(f"Portfolio for user {user.username}: {portfolio}")
    return {"user_id": user.id, "portfolio": portfolio}


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
