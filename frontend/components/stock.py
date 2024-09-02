from frontend.components.portfolio import PortfolioManager
from frontend.api.client import APIClient
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from scipy import stats
import yfinance as yf
import pandas as pd
import requests
import warnings

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


def create_chart(df, x, y, title, color):
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


def show_analysis_tab(api_client: APIClient):
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


def show_portfolio_summary(api_client: APIClient):
    st.subheader("Portfolio Summary")

    portfolio_response = api_client.fetch_portfolio(st.session_state.token)

    if not portfolio_response or not isinstance(portfolio_response, dict):
        st.error("Failed to fetch or parse portfolio data.")
        return

    portfolio = portfolio_response.get("portfolio", [])

    if not portfolio:
        st.info("Your portfolio is empty. Add some stocks to see the summary.")
        return

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
    col4, col5 = st.columns(2)
    col4.metric("Overall Percentage Gain/Loss", f"{total_percentage_gain_loss:.2f}%")

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


def show_stock_analysis(api_client: APIClient, symbol, analysis):
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

    col1, col2, col3 = st.columns(3)
    col1.metric("Current Price", f"${current_price:.2f}")
    col2.metric("Volatility", f"{analysis['volatility']:.2%}")

    beta = calculate_beta(df)
    col3.metric("Beta", f"{beta:.2f}" if beta is not None else "N/A")

    fig = create_chart(
        df,
        "Date",
        "Close",
        f"Closing Price Over Time ({symbol})",
        color="rgba(0,255,0,0.7)",
    )
    st.plotly_chart(fig, use_container_width=True)

    if st.checkbox(f"Show Moving Averages ({symbol})"):
        show_moving_averages(df, symbol)

    fig_volume = create_chart(
        df,
        x="Date",
        y="Volume",
        title=f"Trading Volume ({symbol})",
        color="rgba(0,255,0,0.7)",
    )
    st.plotly_chart(fig_volume, use_container_width=True)


def calculate_beta(df):
    try:
        start_date = df["Date"].min()
        end_date = df["Date"].max()

        market_data = yf.download("^GSPC", start=start_date, end=end_date)
        if market_data.empty:
            return None

        df = df.set_index("Date")
        market_data = market_data["Close"].pct_change().dropna()

        stock_returns = df["Close"].pct_change().dropna()
        combined_data = pd.concat([stock_returns, market_data], axis=1).dropna()
        combined_data.columns = ["stock_returns", "market_returns"]

        if len(combined_data) > 1:
            beta, _, _, _, _ = stats.linregress(
                combined_data["market_returns"], combined_data["stock_returns"]
            )
            return beta
        else:
            return None
    except Exception as e:
        print(f"Error calculating beta: {e}")
        return None


def show_moving_averages(df, symbol):
    df["MA50"] = df["Close"].rolling(window=50).mean()
    df["MA200"] = df["Close"].rolling(window=200).mean()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Date"], y=df["Close"], name="Close"))
    fig.add_trace(go.Scatter(x=df["Date"], y=df["MA50"], name="50-day MA"))
    fig.add_trace(go.Scatter(x=df["Date"], y=df["MA200"], name="200-day MA"))
    fig.update_layout(title=f"Moving Averages for {symbol}")
    st.plotly_chart(fig, use_container_width=True)
