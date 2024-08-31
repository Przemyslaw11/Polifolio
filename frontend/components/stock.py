from frontend.api.client import APIClient
from datetime import datetime, timedelta
import plotly.express as px
import streamlit as st
import pandas as pd
import requests


def show_add_stock_tab(api_client: APIClient) -> None:
    """
    Display the add stock tab and handle stock addition.

    Args:
        api_client (APIClient): The API client instance for making requests.
    """
    symbol = st.text_input("Stock Symbol")
    quantity = st.number_input("Quantity", min_value=1, step=1, format="%d")
    purchase_price = st.number_input("Purchase Price", min_value=0.01, step=0.01)

    if st.button("Add Stock"):
        if "user_id" in st.session_state:
            if api_client.add_stock(
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


def show_real_time_stock_prices_tab(api_client: APIClient) -> None:
    """
    Display the real-time stock prices tab and handle stock price fetching.

    Args:
        api_client (APIClient): The API client instance for making requests.
    """
    stock_symbol = st.text_input("Enter Stock Symbol for Price", "AAPL")
    if st.button("Get Stock Price"):
        stock_price = api_client.fetch_stock_price(stock_symbol)
        if stock_price:
            st.write(f"{stock_symbol} Stock Price: {stock_price.get('price', 'N/A')}")
        else:
            st.error("Failed to fetch stock price")


def get_date_range(start_str, end_str):
    today = datetime.now()

    def parse_date_str(date_str):
        if "year" in date_str:
            years = int(date_str.split()[0])
            return today - timedelta(days=365 * years)
        elif "month" in date_str:
            months = int(date_str.split()[0])
            return today - timedelta(days=30 * months)
        elif "day" in date_str:
            days = int(date_str.split()[0])
            return today - timedelta(days=days)
        else:
            return today

    start_date = parse_date_str(start_str)
    end_date = parse_date_str(end_str)

    return pd.date_range(start=start_date, end=end_date)


def show_analysis_tab():
    ticker_symbol = st.text_input("Enter stock symbol", "AAPL")

    if st.button("Analyze Stock"):
        try:
            response = requests.get(
                f"http://fastapi_app:8000/stocks/analysis/{ticker_symbol}"
            )
            response.raise_for_status()
            data = response.json()

            df = pd.DataFrame(data["historical_data"])
            df["Date"] = pd.to_datetime(df["Date"])

            st.subheader("Closing Price Over Time")
            fig = px.line(df, x="Date", y="Close", title="Closing Price Over Time")
            st.plotly_chart(fig)

            portfolio_df = pd.DataFrame(data["portfolio_value"])
            portfolio_df["Date"] = pd.to_datetime(portfolio_df["Date"])
            st.subheader("Portfolio Value Over Time")
            fig = px.line(
                portfolio_df,
                x="Date",
                y="Portfolio Value",
                title="Portfolio Value Over Time",
            )
            st.plotly_chart(fig)

            st.subheader("Volatility of Returns")
            st.write(f"Annualized Volatility: {data['volatility']:.2%}")

            profit_df = pd.DataFrame(data["profit_over_time"])
            profit_df["Date"] = pd.to_datetime(profit_df["Date"])
            st.subheader("Profit Over Time")
            fig = px.line(
                profit_df, x="Date", y="Cumulative Returns", title="Profit Over Time"
            )
            st.plotly_chart(fig)

            investment_df = pd.DataFrame(data["investment_value_over_time"])
            investment_df["Date"] = pd.to_datetime(investment_df["Date"])
            st.subheader("Investment Value Over Time")
            fig = px.line(
                investment_df, x="Date", y="Close", title="Investment Value Over Time"
            )
            st.plotly_chart(fig)

            asset_df = pd.DataFrame(data["asset_value_over_time"])
            asset_df["Date"] = pd.to_datetime(asset_df["Date"])
            st.subheader("Asset Value Over Time")
            fig = px.line(
                asset_df, x="Date", y="Portfolio Value", title="Asset Value Over Time"
            )
            st.plotly_chart(fig)

            dividends_df = pd.DataFrame(data["dividends"])
            if not dividends_df.empty:
                dividends_df["Date"] = pd.to_datetime(dividends_df["Date"])
                st.subheader("Dividends Over Time")
                fig = px.bar(
                    dividends_df, x="Date", y="Dividends", title="Dividends Over Time"
                )
                st.plotly_chart(fig)
            else:
                st.info("No dividend data available for this stock.")

        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching data: {e}")
        except ValueError as e:
            st.error(f"Data processing error: {e}")
