"""Centralized structured logging for Football Intelligence Platform.

Provides standardized format with timestamps, log levels, and module identifiers,
fulfilling Week 5 Sections 40-42 requirements.
"""

import os
import sys
import logging
from typing import Optional


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """Returns a standardized structured logger with timestamps and component tagging.

    Args:
        name: Name of the component/module requesting the logger.
        level: Optional log level override (e.g., 'DEBUG', 'INFO', 'WARNING', 'ERROR').

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(name)
    
    # Determine effective level
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO").upper()
    numeric_level = getattr(logging, level, logging.INFO)
    logger.setLevel(numeric_level)

    # Avoid adding duplicate handlers if already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(numeric_level)
        
        # Format: 2026-09-22 12:00:00 [INFO] [api.main]: Message
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False

    return logger
