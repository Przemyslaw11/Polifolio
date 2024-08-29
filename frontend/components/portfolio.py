from frontend.config import STOCK_PRICES_INTERVAL_UPDATES_SECONDS
from frontend.api.client import APIClient
from typing import List, Dict, Tuple
import streamlit as st
import pandas as pd
import time


class PortfolioManager:
    @staticmethod
    def calculate_portfolio_metrics(
        portfolio: List[Dict],
    ) -> Tuple[float, float, float]:
        """
        Calculate portfolio metrics based on the given portfolio data.

        Args:
            portfolio (List[Dict]): List of dictionaries containing stock data.

        Returns:
            Tuple[float, float, float]: Total value, total gain/loss, and total percentage gain/loss.
        """
        total_value = sum(stock["current_value"] for stock in portfolio)
        total_gain_loss = sum(stock["gain_loss"] for stock in portfolio)
        total_investment = sum(
            stock["quantity"] * stock["purchase_price"] for stock in portfolio
        )
        total_percentage_gain_loss = (
            (total_gain_loss / total_investment) * 100 if total_investment > 0 else 0
        )

        return total_value, total_gain_loss, total_percentage_gain_loss

    @staticmethod
    def format_portfolio_dataframe(portfolio: List[Dict]) -> pd.DataFrame:
        """
        Format the portfolio data into a pandas DataFrame.

        Args:
            portfolio (List[Dict]): List of dictionaries containing stock data.

        Returns:
            pd.DataFrame: Formatted DataFrame containing portfolio information.
        """
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
            (df["Profit/Loss"] / (df["Quantity"] * df["Purchase Price"])) * 100
        ).round(2)
        df["Quantity"] = df["Quantity"].astype(int)
        df["Purchase Price"] = df["Purchase Price"].apply(lambda x: f"${x:,.2f}")
        df["Current Price"] = df["Current Price"].apply(lambda x: f"${x:,.2f}")
        df["Current Value"] = df["Current Value"].apply(lambda x: f"${x:,.2f}")
        df["Profit/Loss"] = df["Profit/Loss"].apply(
            lambda x: f"${x:,.2f}" if x >= 0 else f"$-{abs(x):,.2f}"
        )
        df["Percentage Gain/Loss (%)"] = df["Percentage Gain/Loss (%)"].apply(
            lambda x: f"{x:.2f}%" if x >= 0 else f"-{abs(x):.2f}%"
        )

        return df


def show_view_portfolio_tab(api_client: APIClient) -> None:
    """
    Display the view portfolio tab and handle portfolio data fetching and display.

    Args:
        api_client (APIClient): The API client instance for making requests.
    """
    portfolio_manager = PortfolioManager()
    placeholder = st.empty()

    while True:
        portfolio_data = api_client.fetch_portfolio(st.session_state.token)

        with placeholder.container():
            if portfolio_data:
                portfolio = portfolio_data.get("portfolio", [])
                if portfolio:
                    df = portfolio_manager.format_portfolio_dataframe(portfolio)
                    total_value, total_gain_loss, total_percentage_gain_loss = (
                        portfolio_manager.calculate_portfolio_metrics(portfolio)
                    )

                    st.dataframe(df, hide_index=True)

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric(
                            label="Total Portfolio Value", value=f"${total_value:,.2f}"
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

        time.sleep(STOCK_PRICES_INTERVAL_UPDATES_SECONDS)
