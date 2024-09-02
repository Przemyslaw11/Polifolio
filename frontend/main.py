from components.stock import (
    show_add_stock_tab,
    show_real_time_stock_prices_tab,
    show_analysis_tab,
)
from components.portfolio import show_view_portfolio_tab
from utils.background_manager import set_background
from config import BACKGROUND_IMAGE_PATH, logger
from components.login import show_login_page
from api.client import APIClient
import streamlit as st


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
            self.show_start_tab()
        with tabs[1]:
            show_add_stock_tab(self.api_client)
        with tabs[2]:
            show_real_time_stock_prices_tab(self.api_client)
        with tabs[3]:
            show_analysis_tab(self.api_client)
        with tabs[4]:
            show_view_portfolio_tab(self.api_client)

    def show_start_tab(self) -> None:
        """
        Display the start tab content.
        """
        st.markdown(self.get_start_tab_html(), unsafe_allow_html=True)

    @staticmethod
    def get_start_tab_html() -> str:
        """
        Generate the HTML content for the start tab.

        Returns:
            str: HTML content for the start tab.
        """
        return f"""
        <style>
        .start-tab {{
            text-align: center;
            color: #ffffff;
        }}
        .start-tab h1 {{
            font-size: 2em;
            margin-bottom: 10px;
            color: #ffffff;
        }}
        .start-tab p {{
            font-size: 1.2em;
            margin-bottom: 20px;
            color: #ffffff;
        }}
        .start-tab ul {{
            list-style: none;
            padding: 0;
            margin: 0;
            font-size: 1.1em;
        }}
        .start-tab li {{
            margin: 10px 0;
        }}
        .start-tab strong {{
            color: #ffffff;
        }}
        </style>

        <div class="start-tab">
            <h1>Welcome, {st.session_state.username}!</h1>
            <p style="text-align: left; padding-left: 20px;">To get started, here's what you can do:</p>
            <p>
                <ul style="list-style-type: none; padding: 0; text-align: left;">
                    <li style="display: inline-block; margin: 0 10px;"><strong>Add Stock:</strong> Easily add new stocks to your portfolio.</li>
                    <li style="display: inline-block; margin: 0 10px;"><strong>Real-Time Stock Prices:</strong> Stay updated with the latest stock prices to make informed decisions.</li>
                    <li style="display: inline-block; margin: 0 10px;"><strong>View Portfolio:</strong> Review your portfolio's performance and track your progress in real time.</li>
                </ul>
            </p>
        </div>
        """


if __name__ == "__main__":
    logger.info("Starting Streamlit app")
    app = StreamlitApp()
    app.run()
