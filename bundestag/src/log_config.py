import logging
from pathlib import Path


def setup_logger():
    # Create a logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Create a file handler
    handler = logging.FileHandler(Path(__file__).parents[2] / "logs" / "bundestag.log", "w")

    # Create a logging format
    formatter = logging.Formatter(
        "%(asctime)s [%(name)s] %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)

    # Add the handler to the logger
    if not logger.handlers:
        logger.addHandler(handler)

    return logger
