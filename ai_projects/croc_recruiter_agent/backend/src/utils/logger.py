import logging
from src.config import get_settings


def get_logger(name: str) -> logging.Logger:
    settings = get_settings()

    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler()

        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
        )

        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger