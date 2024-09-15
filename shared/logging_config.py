from datetime import datetime
import os

from logging.handlers import RotatingFileHandler
import logging
import pytz


def setup_logging(log_file, timezone):
    log_dir = os.path.dirname(log_file)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logger = logging.getLogger("global_logger")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        file_handler = RotatingFileHandler(log_file, maxBytes=10485760, backupCount=10)
        file_handler.setLevel(logging.INFO)

        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s", "function": "%(funcName)s", "source": "%(source)s"}',
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        formatter.converter = lambda timestamp: datetime.fromtimestamp(
            timestamp, tz=pytz.timezone(timezone)
        ).timetuple()

        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger


def get_logger(source):
    logger = logging.getLogger("global_logger")
    return logging.LoggerAdapter(logger, {"source": source})
