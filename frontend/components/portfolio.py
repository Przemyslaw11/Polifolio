from typing import List, Dict, Tuple
import time

import streamlit as st
import pandas as pd

from shared.config import settings
from frontend.api.client import APIClient


class PortfolioManager:
    @staticmethod
    def calculate_portfolio_metrics(
        portfolio: List[Dict],
    ) -> Tuple[float, float, float]:
        """
        Calculate total value, gain/loss, and percentage gain/loss of the portfolio.
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
        Format portfolio data into a pandas DataFrame for display.
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
        df = PortfolioManager.format_currency_columns(df)
        return df

    @staticmethod
    def format_currency_columns(df: pd.DataFrame) -> pd.DataFrame:
        """
        Format columns related to prices, values, and percentages for readability.
        """
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

    @staticmethod
    def calculate_sharpe_ratio(
        portfolio_returns: pd.Series, risk_free_rate: float = 0.01
    ) -> float:
        excess_returns = portfolio_returns.mean() - risk_free_rate
        return excess_returns / portfolio_returns.std()

    @staticmethod
    def calculate_sortino_ratio(
        portfolio_returns: pd.Series, risk_free_rate: float = 0.01
    ) -> float:
        downside_risk = portfolio_returns[portfolio_returns < 0].std()
        excess_returns = portfolio_returns.mean() - risk_free_rate
        return excess_returns / downside_risk if downside_risk > 0 else None


def display_portfolio(
    portfolio_manager: PortfolioManager, portfolio_data: Dict
) -> None:
    """
    Display the portfolio data and metrics in the Streamlit app.
    """
    portfolio = portfolio_data.get("portfolio", [])
    if portfolio:
        df = portfolio_manager.format_portfolio_dataframe(portfolio)
        total_value, total_gain_loss, total_percentage_gain_loss = (
            portfolio_manager.calculate_portfolio_metrics(portfolio)
        )

        st.dataframe(df, hide_index=True)

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Portfolio Value", f"${total_value:,.2f}")
        col2.metric(
            "Overall Profit/Loss",
            f"${total_gain_loss:,.2f}",
            delta=f"{total_gain_loss:,.2f}",
        )
        col3.metric(
            "Overall Percentage Gain/Loss",
            f"{total_percentage_gain_loss:.2f}%",
            delta=f"{total_percentage_gain_loss:.2f}%",
        )
    else:
        st.warning("No stocks in the portfolio.")


def show_view_portfolio_tab(api_client: APIClient) -> None:
    """
    Display the portfolio tab, fetch portfolio data, and show metrics.
    """
    portfolio_manager = PortfolioManager()
    placeholder = st.empty()

    while True:
        portfolio_data = api_client.fetch_portfolio(st.session_state.token)

        with placeholder.container():
            if portfolio_data:
                display_portfolio(portfolio_manager, portfolio_data)
            else:
                st.error("Failed to fetch portfolio")

        time.sleep(int(settings.STOCK_PRICES_INTERVAL_UPDATES_SECONDS / 2))
