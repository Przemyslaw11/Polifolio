from frontend.config import FASTAPI_URL, logger
import streamlit as st
import requests


class APIClient:
    @staticmethod
    def login(username: str, password: str):
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
    def create_user(username: str, email: str, password: str) -> bool:
        response = requests.post(
            f"{FASTAPI_URL}/users/",
            json={"username": username, "email": email, "password": password},
        )
        return response.status_code == 200

    @staticmethod
    def fetch_portfolio(token: str):
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
    def add_stock(
        user_id: str, token: str, symbol: str, quantity: int, purchase_price: float
    ) -> bool:
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
    def fetch_stock_price(symbol: str):
        response = requests.get(f"{FASTAPI_URL}/stocks/{symbol}")
        if response.status_code == 200:
            return response.json()
        return None
