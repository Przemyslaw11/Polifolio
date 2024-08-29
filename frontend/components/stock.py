from frontend.api.client import APIClient
import streamlit as st


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
