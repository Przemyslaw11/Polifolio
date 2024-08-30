from shared.logging_config import setup_logging
from dotenv import load_dotenv
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

load_dotenv()

FASTAPI_URL = "http://fastapi_app:8000"
BACKGROUND_IMAGE_PATH = os.getenv("BACKGROUND_IMAGE_PATH")
STOCK_PRICES_INTERVAL_UPDATES_SECONDS = int(
    os.getenv("STOCK_PRICES_INTERVAL_UPDATES_SECONDS", 15)
)

logger = setup_logging()
