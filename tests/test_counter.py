"""Unit tests for Counter class."""

import pytest
import asyncio
from getback.counter import Counter


@pytest.mark.asyncio
async def test_counter_starts_at_zero():
    """Counter should initialize to 0."""
    counter = Counter()
    assert await counter.get() == 0


@pytest.mark.asyncio
async def test_counter_increment():
    """Counter should increment and return new value."""
    counter = Counter()
    assert await counter.increment() == 1
    assert await counter.increment() == 2
    assert await counter.increment() == 3


@pytest.mark.asyncio
async def test_counter_get_no_increment():
    """get() should return value without incrementing."""
    counter = Counter()
    await counter.increment()
    await counter.increment()

    # Multiple get() calls should return same value
    assert await counter.get() == 2
    assert await counter.get() == 2
    assert await counter.get() == 2


@pytest.mark.asyncio
async def test_counter_concurrent_increments():
    """Counter should handle concurrent increments atomically."""
    counter = Counter()
    num_tasks = 100

    # Create 100 concurrent increment tasks
    tasks = [counter.increment() for _ in range(num_tasks)]
    results = await asyncio.gather(*tasks)

    # Final value should be exactly 100
    assert await counter.get() == num_tasks

    # All results should be unique (no duplicates)
    assert len(set(results)) == num_tasks

    # Results should be 1 through 100 (in some order)
    assert sorted(results) == list(range(1, num_tasks + 1))
