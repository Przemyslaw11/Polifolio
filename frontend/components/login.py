from frontend.api.client import APIClient
from frontend.config import logger
import streamlit as st


def show_login_page() -> None:
    """
    Display the login page with login and create account tabs.
    """
    tab1, tab2 = st.tabs(["Login", "Create Account"])

    with tab1:
        show_login_tab()

    with tab2:
        show_create_account_tab()


def show_login_tab() -> None:
    """
    Display the login tab and handle user login.
    """
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        api_client = APIClient()
        token, user_id = api_client.login(username, password)
        if token and user_id:
            st.session_state.token = token
            st.session_state.user_id = user_id
            st.session_state.username = username
            st.session_state.logged_in = True
            st.success("Logged in successfully!")
            st.rerun()
        else:
            logger.error("Login failed")
            st.error("Login failed. Please check the logs for more information.")


def show_create_account_tab() -> None:
    """
    Display the create account tab and handle user registration.
    """
    api_client = APIClient()
    new_username = st.text_input("New Username")
    new_email = st.text_input("Email")
    new_password = st.text_input("New Password", type="password")
    if st.button("Create Account"):
        if api_client.create_user(new_username, new_email, new_password):
            st.success("Account created successfully! Please log in.")
        else:
            st.error("Failed to create account")
