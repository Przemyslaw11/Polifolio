from fastapi import APIRouter, HTTPException
from dotenv import load_dotenv
import httpx
import os

load_dotenv()

router = APIRouter()

ALPHAVANTAGE_API_KEY = os.getenv('ALPHAVANTAGE_API_KEY')
BASE_URL = 'https://www.alphavantage.co/query'

@router.get("/stocks/{symbol}")
async def get_stock_price(symbol: str):
    if ALPHAVANTAGE_API_KEY is None:
        raise HTTPException(status_code=500, detail="API key is not set")
    
    url = f"{BASE_URL}?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=1min&apikey={ALPHAVANTAGE_API_KEY}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Error fetching data from Alpha Vantage")
        data = response.json()
    try:
        latest_time = next(iter(data["Time Series (1min)"]))
        latest_data = data["Time Series (1min)"][latest_time]
        price = latest_data["1. open"]
    except KeyError:
        raise HTTPException(status_code=404, detail="Stock symbol not found")

    return {"symbol": symbol, "price": price}
