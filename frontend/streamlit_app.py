from shared.logging_config import setup_logging
from background_manager import set_background
from streamlit.components.v1 import html
from dotenv import load_dotenv
import streamlit as st
import pandas as pd
import requests
import os

load_dotenv()

st.set_page_config(layout="wide")

set_background(os.getenv("BACKGROUND_IMAGE_PATH"))

FASTAPI_URL = "http://fastapi_app:8000"

logger = setup_logging()


def login(username, password):
    try:
        response = requests.post(
            f"{FASTAPI_URL}/token", data={"username": username, "password": password}
        )
        logger.info(f"Login response status code: {response.status_code}")
        logger.info(f"Login response content: {response.text}")

        if response.status_code == 200:
            data = response.json()
            return data.get("access_token"), data.get("user_id")
        else:
            logger.error(
                f"Login failed. Status code: {response.status_code}, Response: {response.text}"
            )
        return None, None
    except Exception as e:
        logger.error(f"Exception during login: {str(e)}")
        return None, None


def create_user(username, email, password):
    response = requests.post(
        f"{FASTAPI_URL}/users/",
        json={"username": username, "email": email, "password": password},
    )
    return response.status_code == 200


def fetch_portfolio(token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{FASTAPI_URL}/portfolio", headers=headers)
        logger.info(f"Portfolio response status code: {response.status_code}")
        logger.info(f"Portfolio response content: {response.text}")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error fetching portfolio: {str(e)}")
        st.error(f"Error fetching portfolio: {str(e)}")
        return None


def add_stock(user_id, token, symbol, quantity, purchase_price):
    if user_id is None:
        st.error("User ID is not available")
        return False
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{FASTAPI_URL}/users/{user_id}/stocks/",
        headers=headers,
        json={
            "symbol": symbol,
            "quantity": quantity,
            "purchase_price": purchase_price,
        },
    )
    return response.status_code == 200


def fetch_stock_price(symbol):
    response = requests.get(f"{FASTAPI_URL}/stocks/{symbol}")
    if response.status_code == 200:
        return response.json()
    return None


def calculate_portfolio_metrics(portfolio):
    total_value = sum(stock["current_value"] for stock in portfolio)
    total_gain_loss = sum(stock["gain_loss"] for stock in portfolio)
    total_investment = sum(
        stock["quantity"] * stock["purchase_price"] for stock in portfolio
    )
    total_percentage_gain_loss = (
        (total_gain_loss / total_investment) * 100 if total_investment > 0 else 0
    )

    return total_value, total_gain_loss, total_percentage_gain_loss


def main():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        tab1, tab2 = st.tabs(["Login", "Create Account"])

        with tab1:
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.button("Login"):
                token, user_id = login(username, password)
                if token and user_id:
                    st.session_state.token = token
                    st.session_state.user_id = user_id
                    st.session_state.username = username
                    st.session_state.logged_in = True
                    st.success("Logged in successfully!")
                    st.rerun()
                else:
                    st.error(
                        "Login failed. Please check the logs for more information."
                    )

        with tab2:
            new_username = st.text_input("New Username")
            new_email = st.text_input("Email")
            new_password = st.text_input("New Password", type="password")
            if st.button("Create Account"):
                if create_user(new_username, new_email, new_password):
                    st.success("Account created successfully! Please log in.")
                else:
                    st.error("Failed to create account")

    else:
        st.write(f"Welcome, {st.session_state.username}!")
        if st.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        tabs = st.tabs(["Add Stock", "View Portfolio", "Real-Time Stock Prices"])

        with tabs[0]:
            symbol = st.text_input("Stock Symbol")
            quantity = st.number_input("Quantity", min_value=1, step=1, format="%d")
            purchase_price = st.number_input(
                "Purchase Price", min_value=0.01, step=0.01
            )

            if st.button("Add Stock"):
                if "user_id" in st.session_state:
                    if add_stock(
                        st.session_state.user_id,
                        st.session_state.token,
                        symbol,
                        quantity,
                        purchase_price,
                    ):
                        st.success("Stock added successfully!")
                    else:
                        st.error("Failed to add stock")
                else:
                    st.error("User ID not found. Please log in again.")

        with tabs[1]:
            if st.button("Update"):
                portfolio_data = fetch_portfolio(st.session_state.token)

                if portfolio_data:
                    portfolio = portfolio_data.get("portfolio", [])
                    if portfolio:
                        df = pd.DataFrame(portfolio)
                        df.columns = [
                            "Stock Symbol",
                            "Quantity",
                            "Purchase Price",
                            "Current Price",
                            "Current Value",
                            "Profit/Loss",
                        ]

                        df["Percentage Gain/Loss (%)"] = (
                            (
                                df["Profit/Loss"]
                                / (df["Quantity"] * df["Purchase Price"])
                            )
                            * 100
                        ).round(2)
                        df["Quantity"] = df["Quantity"].astype(int)
                        df["Purchase Price"] = df["Purchase Price"].apply(
                            lambda x: f"${x:,.2f}"
                        )
                        df["Current Price"] = df["Current Price"].apply(
                            lambda x: f"${x:,.2f}"
                        )
                        df["Current Value"] = df["Current Value"].apply(
                            lambda x: f"${x:,.2f}"
                        )
                        df["Profit/Loss"] = df["Profit/Loss"].apply(
                            lambda x: f"${x:,.2f}" if x >= 0 else f"$-{abs(x):,.2f}"
                        )
                        df["Percentage Gain/Loss (%)"] = df[
                            "Percentage Gain/Loss (%)"
                        ].apply(lambda x: f"{x:.2f}%" if x >= 0 else f"-{abs(x):.2f}%")
                        total_value, total_gain_loss, total_percentage_gain_loss = (
                            calculate_portfolio_metrics(portfolio)
                        )

                        st.dataframe(df, hide_index=True)

                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.metric(
                                label="Total Portfolio Value",
                                value=f"${total_value:,.2f}",
                            )
                        with col2:
                            st.metric(
                                label="Overall Profit/Loss",
                                value=f"${total_gain_loss:,.2f}",
                                delta=f"${total_gain_loss:,.2f}",
                            )
                        with col3:
                            st.metric(
                                label="Overall Percentage Gain/Loss",
                                value=f"{total_percentage_gain_loss:.2f}%",
                                delta=f"{total_percentage_gain_loss:.2f}%",
                            )
                    else:
                        st.warning("No stocks in the portfolio.")
                else:
                    st.error("Failed to fetch portfolio")

        with tabs[2]:
            stock_symbol = st.text_input("Enter Stock Symbol for Price", "AAPL")
            if st.button("Get Stock Price"):
                stock_price = fetch_stock_price(stock_symbol)
                if stock_price:
                    st.write(
                        f"{stock_symbol} Stock Price: {stock_price.get('price', 'N/A')}"
                    )
                else:
                    st.error("Failed to fetch stock price")


if __name__ == "__main__":
    main()
