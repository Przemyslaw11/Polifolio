import streamlit as st
import requests

FLASK_API = "http://flask_app:5000/portfolio"
FASTAPI_URL = "http://fastapi_app:8000/stocks/AAPL"


def fetch_portfolio():
    try:
        return requests.get(FLASK_API).json()
    except requests.exceptions.RequestException as e:
        raise e


def fetch_stock_price():
    try:
        return requests.get(FASTAPI_URL).json()
    except requests.exceptions.RequestException as e:
        raise e


def main():
    st.title("Polifolio - Your Smart Portfolio Tracker")

    st.header("Portfolio")
    try:
        portfolio = fetch_portfolio()
        st.write(portfolio)
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch portfolio data: {e}")

    st.header("Real-Time Stock Prices")
    try:
        stock_price = fetch_stock_price()
        st.write(f"AAPL Stock Price: {stock_price.get('price', 'N/A')}")
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch stock price: {e}")


if __name__ == "__main__":
    main()
