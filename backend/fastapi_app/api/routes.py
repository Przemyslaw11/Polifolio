from datetime import timedelta
from typing import List
import warnings

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


from fastapi_app.services.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_password_hash,
)
from fastapi_app.schemas.stock import StockCreate, StockResponse, StockAnalysisResponse
from fastapi_app.schemas.portfolio import (
    PortfolioResponse,
    PortfolioHistoryResponse,
)
from fastapi_app.services.portfolio_service import PortfolioService
from fastapi_app.services.stock_service import StockService
from fastapi_app.schemas.user import UserCreate, Token
from fastapi_app.models.user import User, Stock
from fastapi_app.db.database import get_db
from shared.config import settings, logger

warnings.filterwarnings("ignore", category=FutureWarning)  # yfinance

router = APIRouter()
stock_service = StockService()
portfolio_service = PortfolioService(stock_service)


@router.post("/users/", response_model=UserCreate)
async def create_user(
    user: UserCreate, db: AsyncSession = Depends(get_db)
) -> UserCreate:
    try:
        db_user = User(
            username=user.username,
            email=user.email,
            hashed_password=get_password_hash(user.password),
        )
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return UserCreate(username=db_user.username, email=db_user.email, password="")
    except IntegrityError as e:
        await db.rollback()
        if "unique constraint" in str(e.orig):
            raise HTTPException(
                status_code=400, detail="Username or email already registered."
            )
        raise HTTPException(
            status_code=500, detail="An unexpected database error occurred."
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
) -> Token:
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "user_id": user.id}


@router.post("/users/{user_id}/stocks/", response_model=StockCreate)
async def add_stock(
    user_id: int,
    stock: StockCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Stock:
    if current_user.id != user_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to add stocks for this user"
        )
    db_stock = Stock(**stock.dict(), user_id=user_id)
    db.add(db_stock)
    await db.commit()
    await db.refresh(db_stock)
    return db_stock


@router.get("/portfolio", response_model=PortfolioResponse)
async def get_portfolio(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PortfolioResponse:
    return await portfolio_service.get_user_portfolio(current_user, db)


@router.get("/portfolio/history", response_model=List[PortfolioHistoryResponse])
async def get_portfolio_history_route(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    days: int = 30,
) -> List[PortfolioHistoryResponse]:
    return await portfolio_service.get_portfolio_history(current_user, db, days)


@router.get("/stocks/{symbol}", response_model=StockResponse)
async def get_stock_price(symbol: str) -> StockResponse:
    try:
        stock_data = await stock_service.get_stock_data(symbol)
        return StockResponse(symbol=symbol, price=stock_data["price"])
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching stock data")


@router.get("/portfolio/analysis", response_model=dict)
async def get_portfolio_analysis(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    portfolio_analysis = {}
    user_portfolio = await portfolio_service.get_user_portfolio(current_user, db)

    for stock in user_portfolio.portfolio:
        analysis = await stock_service.analyze_stock(
            stock.symbol, stock.quantity, stock.purchase_price
        )
        portfolio_analysis[stock.symbol] = analysis

    return portfolio_analysis


async def get_stock_analysis(
    symbol: str, quantity: float, purchase_price: float
) -> StockAnalysisResponse:
    try:
        analysis = await stock_service.analyze_stock(symbol, quantity, purchase_price)
        return analysis
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching stock analysis data: {str(e)}"
        )
