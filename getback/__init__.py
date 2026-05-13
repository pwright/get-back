"""Get-Back: Dual-Protocol Counter Service

A simple network service exposing incrementing counters via HTTP and TCP protocols.
"""

import logging


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        Configured logger instance
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger('getback')


__version__ = "1.0.0"
