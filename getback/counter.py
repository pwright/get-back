"""Atomic counter implementation with asyncio.Lock."""

import asyncio


class Counter:
    """Thread-safe counter that increments atomically.

    Each counter instance maintains its own value starting from 0.
    The increment operation is protected by an asyncio.Lock to ensure
    atomicity under concurrent access.
    """

    def __init__(self):
        """Initialize counter at 0 with asyncio.Lock."""
        self._value = 0
        self._lock = asyncio.Lock()

    async def increment(self) -> int:
        """Atomically increment the counter and return new value.

        Returns:
            The new counter value after incrementing
        """
        async with self._lock:
            self._value += 1
            return self._value

    async def get(self) -> int:
        """Get current counter value without incrementing.

        Returns:
            Current counter value
        """
        async with self._lock:
            return self._value
