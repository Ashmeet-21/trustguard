"""
TrustGuard - Logging Setup
Configures loguru for structured logging with console and file output.
"""

import sys
from pathlib import Path
from loguru import logger
from backend.utils import config


def setup_logging():
    """Set up application logging with loguru."""
    # Remove default handler
    logger.remove()

    # Console output - colored and readable
    logger.add(
        sys.stderr,
        level=config.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan> | "
               "<level>{message}</level>",
        colorize=True,
    )

    # File output - rotates at 10MB, keeps 30 days
    log_path = Path(config.LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger.add(
        str(log_path),
        level=config.LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} | {message}",
        rotation="10 MB",
        retention="30 days",
    )

    logger.info("Logging initialized (level={})", config.LOG_LEVEL)
