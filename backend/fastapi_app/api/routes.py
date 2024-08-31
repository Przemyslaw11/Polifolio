from fastapi_app.services.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_password_hash,
)
from fastapi_app.schemas.stock import StockCreate, StockResponse, StockAnalysisResponse
from fastapi_app.schemas.portfolio import PortfolioResponse, PortfolioItem
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi_app.models.user import User, Stock, StockPrice
from fastapi_app.schemas.user import UserCreate, Token
from fastapi.security import OAuth2PasswordRequestForm
from shared.logging_config import setup_logging
from fastapi_app.db.database import get_db
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from datetime import timedelta
import yfinance as yf
import numpy as np
import warnings
import os


logger = setup_logging()
router = APIRouter()

warnings.filterwarnings("ignore", category=FutureWarning)  # yfinance

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15))


@router.post("/users/", response_model=UserCreate)
def create_user(user: UserCreate, db: Session = Depends(get_db)) -> UserCreate:
    """Create a new user in the database."""
    try:
        db_user = User(
            username=user.username,
            email=user.email,
            hashed_password=get_password_hash(user.password),
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return UserCreate(username=db_user.username, email=db_user.email, password="")
    except IntegrityError as e:
        db.rollback()
        if "unique constraint" in str(e.orig):
            raise HTTPException(
                status_code=400, detail="Username or email already registered."
            )
        raise HTTPException(
            status_code=500, detail="An unexpected database error occurred."
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
) -> Token:
    """
    Log in a user and return an access token.
    args:
        - form_data: OAuth2PasswordRequestForm containing username and password
        - db: The database session
    return: A Token object containing access token and token type
    """
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
) -> Stock:
    """
    Add a stock for a user.
    args:
        - user_id: ID of the user to add the stock for
        - stock: StockCreate model containing stock details
        - current_user: The currently authenticated user
        - db: The database session
    return: The added Stock object
    """
    if current_user.id != user_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to add stocks for this user"
        )
    db_stock = Stock(**stock.dict(), user_id=user_id)
    db.add(db_stock)
    db.commit()
    db.refresh(db_stock)
    return db_stock


@router.get("/portfolio", response_model=PortfolioResponse)
def get_user_portfolio(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PortfolioResponse:
    """
    Get the portfolio of the currently authenticated user.

    args:
        - current_user: The currently authenticated user
        - db: The database session

    return: A PortfolioResponse model containing the user ID and a list of PortfolioItem objects.
    """
    user = db.query(User).filter(User.id == current_user.id).first()
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
            current_value = round(stock.quantity * latest_price.price, 3)
            gain_loss = round(
                current_value - (stock.quantity * stock.purchase_price), 3
            )
            portfolio.append(
                PortfolioItem(
                    symbol=stock.symbol,
                    quantity=stock.quantity,
                    purchase_price=stock.purchase_price,
                    current_price=latest_price.price,
                    current_value=current_value,
                    gain_loss=gain_loss,
                )
            )
        else:
            logger.warning(f"No latest price found for stock: {stock.symbol}")

    return PortfolioResponse(user_id=user.id, portfolio=portfolio)


@router.get("/stocks/{symbol}", response_model=StockResponse)
async def get_stock_price(symbol: str) -> StockResponse:
    """
    Get the current price of a stock by symbol.
    args:
        - symbol: The stock symbol to fetch
    return: A StockResponse model containing the stock symbol and its current price
    """
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1mo")
        if data.empty:
            raise HTTPException(status_code=404, detail="Stock symbol not found")
        latest_price = float(round(data["Close"].iloc[-1], 3))
        return StockResponse(symbol=symbol, price=latest_price)
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching stock data")


@router.get("/stocks/analysis/{symbol}", response_model=StockAnalysisResponse)
async def get_stock_analysis(symbol: str) -> StockAnalysisResponse:
    """
    Get stock analysis data including portfolio value, volatility, profit over time, and investment value over time.
    """
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1y")

        if data.empty:
            raise HTTPException(status_code=404, detail="Stock symbol not found")
        
        data = data.reset_index()

        data["Returns"] = data["Close"].pct_change()
        data["Cumulative Returns"] = (1 + data["Returns"]).cumprod()
        data["Portfolio Value"] = (
            data["Cumulative Returns"] * 10000
        )

        dividends_data = ticker.dividends.reset_index()
        if dividends_data.empty:
            dividends = []
        else:
            dividends = dividends_data.to_dict(orient="records")

        volatility = data["Returns"].std() * 252**0.5

        response_data = StockAnalysisResponse(
            historical_data=data.to_dict(orient="records"),
            portfolio_value=data[["Date", "Portfolio Value"]].to_dict(orient="records"),
            volatility=volatility,
            profit_over_time=data[["Date", "Cumulative Returns"]].to_dict(
                orient="records"
            ),
            investment_value_over_time=data[["Date", "Close"]].to_dict(
                orient="records"
            ),
            asset_value_over_time=data[["Date", "Portfolio Value"]].to_dict(
                orient="records"
            ),
            dividends=dividends,
        )

        return response_data

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching stock analysis data: {str(e)}"
        )
