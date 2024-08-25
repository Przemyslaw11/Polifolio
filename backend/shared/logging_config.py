from logging.handlers import RotatingFileHandler
import logging

def setup_logging(log_file="app.log"):
    logger = logging.getLogger("polifolio")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        file_handler = RotatingFileHandler(log_file, maxBytes=10240, backupCount=5)
        file_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger
