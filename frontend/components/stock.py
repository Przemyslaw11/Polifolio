from datetime import datetime, timedelta
import requests
import warnings

import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
import yfinance as yf
import pandas as pd

from frontend.components.portfolio import PortfolioManager
from frontend.api.client import APIClient

warnings.filterwarnings("ignore", category=FutureWarning)  # yfinance


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


def get_date_range(start_str: str, end_str: str) -> pd.DatetimeIndex:
    """
    Generate a date range based on human-readable relative date strings.

    Args:
        start_str (str): A string representing the start date relative to today (e.g., "2 years", "3 months", "10 days").
        end_str (str): A string representing the end date relative to today (e.g., "1 year", "5 days").

    Returns:
        pd.DatetimeIndex: A range of dates from start to end as per the parsed date strings.
    """
    today: datetime = datetime.now()

    def parse_date_str(date_str: str) -> datetime:
        """
        Parse a relative date string into a datetime object based on today's date.

        Args:
            date_str (str): A string representing a relative date (e.g., "2 years", "3 months").

        Returns:
            datetime: The calculated datetime based on the relative date string.
        """
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


def create_chart(df: pd.DataFrame, x: str, y: str, title: str, color: str) -> go.Figure:
    """
    Create a line chart using Plotly.

    Args:
        df (pd.DataFrame): The dataframe containing the data to plot.
        x (str): The column name for the x-axis data.
        y (str): The column name for the y-axis data.
        title (str): The chart title.
        color (str): The color for the line.

    Returns:
        go.Figure: A Plotly line chart.
    """
    fig = px.line(df, x=x, y=y, title=title)
    fig.update_traces(line=dict(color=color, width=2))
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#FFFFFF"),
        title=dict(font=dict(size=24)),
        xaxis=dict(
            title_font=dict(size=18),
            tickfont=dict(size=14),
            gridcolor="rgba(255,255,255,0.1)",
            showline=True,
            linewidth=2,
            linecolor="rgba(255,255,255,0.5)",
        ),
        yaxis=dict(
            title_font=dict(size=18),
            tickfont=dict(size=14),
            gridcolor="rgba(255,255,255,0.1)",
            showline=True,
            linewidth=2,
            linecolor="rgba(255,255,255,0.5)",
        ),
        legend=dict(font=dict(size=14)),
    )
    return fig


def show_analysis_tab(api_client: APIClient) -> None:
    """
    Display the analysis tab and handle portfolio analysis.

    Args:
        api_client (APIClient): The API client instance for making requests.
    """
    response = api_client.fetch_portfolio_analysis(st.session_state.token)
    if response is None or response.status_code != 200:
        st.error("Failed to fetch portfolio analysis data.")
        return

    try:
        portfolio_analysis = response.json()
    except requests.exceptions.JSONDecodeError:
        st.error("Failed to parse portfolio analysis data.")
        return

    if not portfolio_analysis:
        st.info("Your portfolio is empty. Add some stocks to see the analysis.")
        return

    tabs = ["Summary"] + list(portfolio_analysis.keys())
    selected_tab = st.tabs(tabs)

    with selected_tab[0]:
        show_portfolio_summary(api_client)

    for i, symbol in enumerate(portfolio_analysis.keys(), start=1):
        with selected_tab[i]:
            show_stock_analysis(api_client, symbol, portfolio_analysis[symbol])


def create_portfolio_history_chart(history_data: list) -> go.Figure:
    """
    Create a line chart for the portfolio history.

    Args:
        history_data (list): A list of historical portfolio data.

    Returns:
        go.Figure: A Plotly line chart for portfolio history.
    """
    df = pd.DataFrame(history_data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=df["timestamp"], y=df["portfolio_value"], name="Portfolio Value")
    )
    fig.add_trace(
        go.Scatter(x=df["timestamp"], y=df["investment_value"], name="Investment Value")
    )
    fig.add_trace(
        go.Scatter(x=df["timestamp"], y=df["asset_value"], name="Asset Value")
    )

    fig.update_layout(
        title="Portfolio History",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#FFFFFF"),
        xaxis=dict(
            title="Date",
            title_font=dict(size=18),
            tickfont=dict(size=14),
            gridcolor="rgba(255,255,255,0.1)",
            showline=True,
            linewidth=2,
            linecolor="rgba(255,255,255,0.5)",
        ),
        yaxis=dict(
            title="Value ($)",
            title_font=dict(size=18),
            tickfont=dict(size=14),
            gridcolor="rgba(255,255,255,0.1)",
            showline=True,
            linewidth=2,
            linecolor="rgba(255,255,255,0.5)",
        ),
        legend=dict(font=dict(size=14)),
    )

    return fig


def show_portfolio_summary(api_client: APIClient) -> None:
    """
    Display the portfolio summary and handle data fetching and calculation.

    Args:
        api_client (APIClient): The API client instance for making requests.
    """
    st.subheader("Portfolio Summary")

    portfolio_response = api_client.fetch_portfolio(st.session_state.token)

    if not portfolio_response or not isinstance(portfolio_response, dict):
        st.error("Failed to fetch or parse portfolio data.")
        return

    portfolio = portfolio_response.get("portfolio", [])

    if not portfolio:
        st.info("Your portfolio is empty. Add some stocks to see the summary.")
        return

    portfolio_df = pd.DataFrame(portfolio)

    if "symbol" in portfolio_df.columns:
        portfolio_manager = PortfolioManager()

        total_value, total_gain_loss, total_percentage_gain_loss = (
            portfolio_manager.calculate_portfolio_metrics(portfolio)
        )

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Portfolio Value", f"${total_value:,.2f}")
        col2.metric(
            "Total Investment",
            f"${sum(stock['purchase_price'] * stock['quantity'] for stock in portfolio):,.2f}",
        )
        col3.metric("Overall Profit/Loss", f"${total_gain_loss:,.2f}")
        col1_2, col2_2, col3_2 = st.columns(3)
        col1_2.metric(
            "Overall Percentage Gain/Loss", f"{total_percentage_gain_loss:.2f}%"
        )

        historical_data = []
        stock_returns = pd.DataFrame()

        for stock in portfolio:
            symbol = stock["symbol"]
            try:
                data = yf.download(symbol, start="2020-01-01", end=datetime.now())

                if not data.empty:
                    stock_returns[symbol] = data["Close"].pct_change().dropna()
                    historical_data.append(data)
                else:
                    st.warning(f"No data available for {symbol}")
            except Exception as e:
                st.warning(f"Failed to download data for {symbol}: {str(e)}")

        if not stock_returns.empty:
            sharpe_ratio = portfolio_manager.calculate_sharpe_ratio(
                stock_returns.mean(axis=1)
            )
            sortino_ratio = portfolio_manager.calculate_sortino_ratio(
                stock_returns.mean(axis=1)
            )
            correlation_matrix = stock_returns.corr()

            col2_2.metric("Sharpe Ratio", f"{sharpe_ratio:.2f}")
            col3_2.metric("Sortino Ratio", f"{sortino_ratio:.2f}")

        else:
            st.warning("Not enough data to calculate risk metrics.")

        history_data = api_client.fetch_portfolio_history(st.session_state.token)
        if history_data:
            if isinstance(history_data, list):
                fig = create_portfolio_history_chart(history_data)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Unexpected data format for history data.")
                st.write(history_data)
        else:
            st.warning("Unable to fetch portfolio history data.")

        allocation_data = [
            (stock["symbol"], stock["current_value"] / total_value * 100)
            for stock in portfolio
        ]
        allocation_df = pd.DataFrame(allocation_data, columns=["Symbol", "Allocation"])

        st.subheader("Stock Allocation")
        fig = px.pie(
            allocation_df,
            names="Symbol",
            values="Allocation",
            labels={"Symbol": "Symbol", "Allocation": "Allocation (%)"},
        )

        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#FFFFFF"),
            legend=dict(font=dict(size=14)),
        )
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Correlation Matrix")
        if not stock_returns.empty:
            try:
                colors = [
                    "#3D3000",
                    "#704D00",
                    "#A37000",
                    "#D69300",
                    "#FFB300",
                ]

                fig = px.imshow(
                    correlation_matrix,
                    color_continuous_scale=colors,
                    zmin=-1,
                    zmax=1,
                    aspect="auto",
                )
                fig.update_layout(
                    title_text=" ",
                    title_x=0.5,
                    width=700,
                    height=600,
                    xaxis_title="Stocks",
                    yaxis_title="Stocks",
                    coloraxis_colorbar=dict(
                        title="Correlation",
                        thicknessmode="pixels",
                        thickness=20,
                        lenmode="pixels",
                        len=300,
                        yanchor="middle",
                        y=0.5,
                        xanchor="left",
                        x=1.05,
                    ),
                    font=dict(size=12, color="white"),
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                )
                fig.update_xaxes(side="top")
                for i in range(len(correlation_matrix.columns)):
                    for j in range(len(correlation_matrix.index)):
                        fig.add_annotation(
                            x=i,
                            y=j,
                            text=str(round(correlation_matrix.iloc[j, i], 2)),
                            showarrow=False,
                            font=dict(
                                color=(
                                    "black"
                                    if abs(correlation_matrix.iloc[j, i]) > 0.3
                                    else "white"
                                )
                            ),
                        )
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error creating correlation matrix: {str(e)}")
        else:
            st.warning("Not enough data to create correlation matrix.")
    else:
        st.error("Portfolio data does not contain 'symbol' column.")


def show_stock_analysis(api_client: APIClient, symbol: str, analysis: dict) -> None:
    """
    Display the stock analysis for a given stock symbol, including historical data,
    real-time stock price, and volatility. Provides an option to show moving averages.

    Args:
        api_client (APIClient): The API client instance for making requests.
        symbol (str): The stock symbol to analyze.
        analysis (dict): The analysis data, including historical data and volatility.
    """
    if "error" in analysis:
        st.error(f"Failed to fetch analysis for {symbol}: {analysis['error']}")
        return

    if "historical_data" not in analysis:
        st.warning(f"No historical data available for {symbol}")
        return

    df = pd.DataFrame(analysis["historical_data"])
    df["Date"] = pd.to_datetime(df["Date"], utc=True)

    stock_price_data = api_client.fetch_stock_price(symbol)
    if stock_price_data and "price" in stock_price_data:
        current_price = stock_price_data["price"]
    else:
        st.error(f"Failed to fetch real-time price for {symbol}")
        return

    col1, col2 = st.columns(2)
    col1.metric("Current Price", f"${current_price:.2f}")
    col2.metric("Volatility", f"{analysis['volatility']:.2%}")

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["Close"],
            mode="lines",
            name="Close",
            line=dict(color="rgba(0,255,0,0.7)", width=2),
        )
    )

    show_ma = st.checkbox(f"Show Moving Averages ({symbol})")

    if show_ma:
        df["MA50"] = df["Close"].rolling(window=50).mean()
        df["MA200"] = df["Close"].rolling(window=200).mean()

        fig.add_trace(
            go.Scatter(
                x=df["Date"],
                y=df["MA50"],
                mode="lines",
                name="50-day MA",
                line=dict(color="rgba(255,165,0,0.7)", width=2),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df["Date"],
                y=df["MA200"],
                mode="lines",
                name="200-day MA",
                line=dict(color="rgba(0,0,255,0.7)", width=2),
            )
        )

    fig.update_layout(
        title=f"Closing Price Over Time ({symbol})",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#FFFFFF"),
        xaxis=dict(
            title_font=dict(size=18),
            tickfont=dict(size=14),
            gridcolor="rgba(255,255,255,0.1)",
            showline=True,
            linewidth=2,
            linecolor="rgba(255,255,255,0.5)",
        ),
        yaxis=dict(
            title_font=dict(size=18),
            tickfont=dict(size=14),
            gridcolor="rgba(255,255,255,0.1)",
            showline=True,
            linewidth=2,
            linecolor="rgba(255,255,255,0.5)",
        ),
        legend=dict(font=dict(size=14)),
    )

    st.plotly_chart(fig, use_container_width=True)

    fig_volume = create_chart(
        df,
        x="Date",
        y="Volume",
        title=f"Trading Volume ({symbol})",
        color="rgba(0,255,0,0.7)",
    )
    st.plotly_chart(fig_volume, use_container_width=True)
