"""Measure what async changes. Run with:  pytest

Each test sends several requests AT THE SAME TIME and measures the total time.
Assertions compare timings with each other (not with fixed numbers), so they
hold on slow and fast machines.
"""

import asyncio
import time

import httpx
import pytest

from app import slow_io
from app.main import app

REQUESTS = 5


@pytest.fixture
async def client(monkeypatch):
    monkeypatch.setattr(slow_io, "DELAY", 0.1)
    # Run the lifespan by hand (httpx does not), then talk to the app in-process.
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


async def total_time(client, path: str, requests: int = 1) -> float:
    """Send `requests` identical requests at the same time; return the seconds taken."""
    start = time.perf_counter()
    responses = await asyncio.gather(*[client.get(path) for _ in range(requests)])
    assert all(r.status_code == 200 for r in responses)
    return time.perf_counter() - start


async def test_non_blocking_requests_overlap(client):
    elapsed = await total_time(client, "/demo/non-blocking", REQUESTS)
    assert elapsed < slow_io.DELAY * 3          # about 1 x DELAY, not 5 x


async def test_def_endpoints_run_in_a_thread_pool_and_overlap(client):
    elapsed = await total_time(client, "/demo/threadpool", REQUESTS)
    assert elapsed < slow_io.DELAY * 3


async def test_blocking_code_inside_async_def_makes_requests_queue_up(client):
    elapsed = await total_time(client, "/demo/blocking", REQUESTS)
    assert elapsed >= slow_io.DELAY * (REQUESTS - 0.5)      # about 5 x DELAY


async def test_gather_is_faster_than_awaiting_one_call_after_the_other(client):
    sequential = await total_time(client, "/orders/1001/overview-sequential")
    concurrent = await total_time(client, "/orders/1001/overview")
    assert sequential > concurrent * 1.5        # about 2 x DELAY against 1 x DELAY
