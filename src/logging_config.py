"""Logging configuration for the application."""
import logging
import sys
from typing import Optional


def setup_logging(
    level: int = logging.INFO,
    log_format: Optional[str] = None,
    enable_streamlit_handler: bool = True,
) -> logging.Logger:
    """Configure application logging.

    Args:
        level: Logging level (default: INFO).
        log_format: Custom log format string.
        enable_streamlit_handler: Whether to add a Streamlit-aware handler.

    Returns:
        The configured root logger.
    """
    if log_format is None:
        log_format = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"

    # Configure root logger
    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    # Reduce noise from external libraries
    logging.getLogger("fastf1").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    logger = logging.getLogger("explain_strategy")
    logger.debug("Logging configured at level %s", logging.getLevelName(level))

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name.

    Args:
        name: Logger name (typically __name__).

    Returns:
        Configured logger instance.
    """
    return logging.getLogger(f"explain_strategy.{name}")
