"""Pytest configuration and fixtures."""

import pytest


@pytest.fixture
def random_ports():
    """Generate random port numbers for testing.

    Returns:
        Tuple of (http_port, tcp_port) using high port numbers
    """
    import random
    base = random.randint(10000, 50000)
    return (base, base + 1)
