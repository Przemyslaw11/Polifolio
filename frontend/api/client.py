from typing import Tuple, Optional, Dict, Any, List
from frontend.config import FASTAPI_URL, logger
import streamlit as st
import requests


class APIClient:
    @staticmethod
    def login(username: str, password: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Authenticate user and retrieve access token and user ID.

        Args:
            username (str): User's username.
            password (str): User's password.

        Returns:
            Tuple[Optional[str], Optional[str]]: Access token and user ID if successful, None otherwise.
        """
        try:
            response = requests.post(
                f"{FASTAPI_URL}/token",
                data={"username": username, "password": password},
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

    @staticmethod
    def create_user(
        username: str, email: str, password: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Create a new user account.

        Args:
            username (str): New user's username.
            email (str): New user's email.
            password (str): New user's password.

        Returns:
            Tuple[bool, Optional[str]]: True if account creation was successful, False otherwise, along with an error message.
        """
        try:
            response = requests.post(
                f"{FASTAPI_URL}/users/",
                json={"username": username, "email": email, "password": password},
            )
            if response.status_code == 200:
                return True, "Account created successfully! Please log in."
            else:
                error_message = response.json().get("detail", "Unknown error occurred.")
                if "already registered" in error_message.lower():
                    return False, "Username or email already registered."
                return False, error_message
        except Exception as e:
            return False, str(e)

    @staticmethod
    def fetch_portfolio(token: str):
        """
        Retrieve the user's portfolio.

        Args:
            token (str): Bearer token for authorization.

        Returns:
            Optional[Dict[str, Any]]: Portfolio data if successful, None otherwise.
        """
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

    @staticmethod
    def fetch_portfolio_history(token: str, days: int = 30) -> Optional[List[Dict[str, Any]]]:
        headers = {"Authorization": f"Bearer {token}"}
        try:
            url = f"{FASTAPI_URL}/portfolio/history?days={days}"
            logger.info(f"Fetching portfolio history from URL: {url}")
            logger.info(f"Headers: {headers}")
            
            response = requests.get(url, headers=headers)
            
            logger.info(f"Portfolio history response status code: {response.status_code}")
            logger.info(f"Portfolio history response content: {response.text}")
            
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching portfolio history: {str(e)}")
            st.error(f"Error fetching portfolio history: {str(e)}")
            return None

    @staticmethod
    def add_stock(
        user_id: str, token: str, symbol: str, quantity: int, purchase_price: float
    ) -> bool:
        """
        Add a stock to the user's portfolio.

        Args:
            user_id (str): The ID of the user.
            token (str): Bearer token for authorization.
            symbol (str): Stock symbol to add.
            quantity (int): Number of shares to add.
            purchase_price (float): Purchase price per share.

        Returns:
            bool: True if the stock was added successfully, False otherwise.
        """
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

    @staticmethod
    def fetch_stock_price(symbol: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the current price of a stock.

        Args:
            symbol (str): The stock symbol to fetch the price for.

        Returns:
            Optional[Dict[str, Any]]: Stock price data if successful, None otherwise.
        """
        response = requests.get(f"{FASTAPI_URL}/stocks/{symbol}")
        if response.status_code == 200:
            return response.json()
        return None

    def fetch_portfolio_analysis(self, token: str):
        headers = {"Authorization": f"Bearer {token}"}
        try:
            response = requests.get(
                f"{FASTAPI_URL}/portfolio/analysis", headers=headers
            )
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error(f"Error fetching portfolio analysis: {str(e)}")
            return None
