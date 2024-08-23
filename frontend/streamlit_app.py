import streamlit as st
import requests

FLASK_API = "http://flask_app:5000/portfolio"
FASTAPI_URL = "http://fastapi_app:8000/stocks/AAPL"

st.title("Polifolio - Your Smart Portfolio Tracker")

st.header("Portfolio")
try:
    portfolio = requests.get(FLASK_API).json()
    st.write(portfolio)
except requests.exceptions.RequestException as e:
    st.error(f"Failed to fetch portfolio data: {e}")

st.header("Real-Time Stock Prices")
try:
    stock_price = requests.get(FASTAPI_URL).json()
    st.write(f"AAPL Stock Price: {stock_price.get('price', 'N/A')}")
except requests.exceptions.RequestException as e:
    st.error(f"Failed to fetch stock price: {e}")
