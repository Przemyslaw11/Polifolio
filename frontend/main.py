import streamlit as st

from components.stock import (
    show_add_stock_tab,
    show_real_time_stock_prices_tab,
    show_analysis_tab,
)
from components.start import show_start_tab
from components.portfolio import show_view_portfolio_tab
from utils.background_manager import set_background
from config import BACKGROUND_IMAGE_PATH, logger
from components.login import show_login_page
from api.client import APIClient


class StreamlitApp:
    def __init__(self):
        st.set_page_config(layout="wide")
        set_background(BACKGROUND_IMAGE_PATH)
        self.api_client = APIClient()

    def run(self) -> None:
        """
        Run the Streamlit application.
        """
        if "logged_in" not in st.session_state:
            st.session_state.logged_in = False

        if not st.session_state.logged_in:
            show_login_page()
        else:
            self.show_main_page()

    def show_main_page(self) -> None:
        """
        Display the main page of the application.
        """
        if st.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        tabs = st.tabs(
            [
                "Start",
                "Add Stock",
                "Real-Time Stock Prices",
                "Portfolio Analysis",
                "View Portfolio",
            ]
        )

        with tabs[0]:
            show_start_tab()
        with tabs[1]:
            show_add_stock_tab(self.api_client)
        with tabs[2]:
            show_real_time_stock_prices_tab(self.api_client)
        with tabs[3]:
            show_analysis_tab(self.api_client)
        with tabs[4]:
            show_view_portfolio_tab(self.api_client)


if __name__ == "__main__":
    logger.info("Starting Streamlit app")
    app = StreamlitApp()
    app.run()
