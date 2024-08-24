import streamlit as st
import requests

FLASK_API = "http://flask_app:5000/portfolio"
FASTAPI_URL = "http://fastapi_app:8000"


def fetch_portfolio():
    try:
        return requests.get(FLASK_API).json()
    except requests.exceptions.RequestException as e:
        raise e


def fetch_stock_price(symbol):
    try:
        return requests.get(f"{FASTAPI_URL}/stocks/{symbol}").json()
    except requests.exceptions.RequestException as e:
        raise e


def main():
    st.title("Polifolio - Your Smart Portfolio Tracker")

    st.header("User Management")
    username = st.text_input("Username")
    email = st.text_input("Email")
    if st.button("Create User"):
        response = requests.post(
            f"{FASTAPI_URL}/users/", json={"username": username, "email": email}
        )
        if response.status_code == 200:
            st.success("User created successfully!")
        else:
            st.error("Failed to create user")

    st.header("Portfolio Management")
    user_id = st.number_input("User ID", min_value=1, step=1)
    symbol = st.text_input("Stock Symbol")
    quantity = st.number_input("Quantity", min_value=0.01, step=0.01)
    purchase_price = st.number_input("Purchase Price", min_value=0.01, step=0.01)

    if st.button("Add Stock"):
        response = requests.post(
            f"{FASTAPI_URL}/users/{user_id}/stocks/",
            json={
                "symbol": symbol,
                "quantity": quantity,
                "purchase_price": purchase_price,
            },
        )
        if response.status_code == 200:
            st.success("Stock added successfully!")
        else:
            st.error("Failed to add stock")

    if st.button("View Portfolio"):
        response = requests.get(f"{FASTAPI_URL}/users/{user_id}/portfolio")
        if response.status_code == 200:
            portfolio = response.json()["portfolio"]
            st.write(portfolio)
        else:
            st.error("Failed to fetch portfolio")

    st.header("Real-Time Stock Prices")
    stock_symbol = st.text_input("Enter Stock Symbol for Price", "AAPL")
    if st.button("Get Stock Price"):
        try:
            stock_price = fetch_stock_price(stock_symbol)
            st.write(f"{stock_symbol} Stock Price: {stock_price.get('price', 'N/A')}")
        except requests.exceptions.RequestException as e:
            st.error(f"Failed to fetch stock price: {e}")

    st.header("Your Portfolio")
    try:
        portfolio = fetch_portfolio()
        st.write(portfolio)
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch portfolio data: {e}")


if __name__ == "__main__":
    main()
