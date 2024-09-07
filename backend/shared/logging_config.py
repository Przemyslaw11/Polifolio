from datetime import datetime
import logging

from logging.handlers import RotatingFileHandler
import pytz


def setup_logging(log_file: str = "app.log") -> logging.Logger:
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logging.basicConfig()
    logger.propagate = False

    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        file_handler = RotatingFileHandler(log_file, maxBytes=10485760, backupCount=10)
        file_handler.setLevel(logging.INFO)

        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s", "function": "%(funcName)s"}',
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        formatter.converter = lambda timestamp: datetime.fromtimestamp(
            timestamp, tz=pytz.timezone("Europe/Warsaw")
        ).timetuple()

        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
        sqlalchemy_logger.setLevel(logging.INFO)
        sqlalchemy_logger.addHandler(console_handler)
        sqlalchemy_logger.addHandler(file_handler)

    return logger
