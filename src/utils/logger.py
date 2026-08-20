"""
Structured logging configuration for the benchmark pipeline.
"""

import logging
import sys
import pathlib
from logging.handlers import RotatingFileHandler


def setup_logger(name: str) -> logging.Logger:
    """
    Configure and return a logger with both console and file output.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    if logger.handlers:  # Already configured
        return logger
    
    logger.setLevel(logging.DEBUG)
    
    # Format specification
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler (INFO and above)
    console_handler = logging.StreamHandler(
        open(sys.stdout.fileno(), mode="w", encoding="utf-8", errors="replace", buffering=1, closefd=False)
)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (DEBUG and above, rotating)
    try:
        # Ensure logs directory exists
        root_dir = pathlib.Path(__file__).resolve().parents[2]
        logs_dir = root_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            str(logs_dir / 'benchmark.log'),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except (OSError, IOError) as e:
        logger.warning(f"Could not create log file handler: {e}")
    
    return logger
