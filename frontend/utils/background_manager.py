import streamlit as st
import base64


def set_background(image_path):
    """
    Function to set the background image with a dark overlay for the Streamlit app.

    Parameters:
    - image_path: The path to the image file to be used as the background.
    """
    with open(image_path, "rb") as image_file:
        image_bytes = image_file.read()
        encoded_image = base64.b64encode(image_bytes).decode()

    page_bg_img = f"""
    <style>
    .stApp {{
        background-image: url("data:image/jpg;base64,{encoded_image}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
        position: relative;
        min-height: 100vh; /* Ensure it takes at least the full viewport height */
        overflow: auto; /* Allow scrolling if content exceeds the viewport */
    }}
    .stApp::before {{
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.7);
        z-index: 1;
    }}
    .stApp > div {{
        position: relative;
        z-index: 2;
        padding: 20px; /* Add some padding for better spacing */
    }}
    header {{
        visibility: hidden;
    }}
    footer {{
        visibility: hidden;
    }}
    </style>
    """
    st.markdown(page_bg_img, unsafe_allow_html=True)
