import streamlit as st 

def show_start_tab() -> None:
    """
    Display the start tab content.
    """
    st.markdown(get_start_tab_html(), unsafe_allow_html=True)

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
                <li style="display: inline-block; margin: 0 10px;">
                    <strong>Portfolio Analysis:</strong> Gain insights with a comprehensive overview of your portfolio's performance and stock allocation.
                    <ul style="list-style-type: disc; padding-left: 40px; margin: 0;"> <!-- Increased padding-left for indentation -->
                        <li style="margin-bottom: 5px;"><strong>Volatility:</strong> Understand the price fluctuations of your stocks over time.</li>
                        <li style="margin-bottom: 5px;"><strong>Beta:</strong> Measure the stock's risk in relation to the market.</li>
                        <li style="margin-bottom: 5px;"><strong>Closing Price Over Time:</strong> Track the historical closing prices of your stocks.</li>
                        <li style="margin-bottom: 5px;"><strong>Moving Averages:</strong> Analyze trends with short-term and long-term moving averages.</li>
                        <li style="margin-bottom: 5px;"><strong>Trading Volume:</strong> Monitor the volume of trades for each stock in your portfolio.</li>
                    </ul>
                </li>
                <li style="display: inline-block; margin: 0 10px;"><strong>View Portfolio:</strong> Review your portfolio's performance and track your progress in real time.</li>
            </ul>
        </p>
    </div>
    """