"""Print the timings that tests/test_concurrency.py checks.

Run it from this folder:   python timing_demo.py
"""

import asyncio
import time

import httpx

from app import slow_io
from app.main import app

REQUESTS = 5


async def measure(client: httpx.AsyncClient, path: str, requests: int) -> float:
    """Send `requests` requests at the same time and return the seconds taken."""
    start = time.perf_counter()
    await asyncio.gather(*[client.get(path) for _ in range(requests)])
    return time.perf_counter() - start


async def main() -> None:
    slow_io.DELAY = 0.2
    async with app.router.lifespan_context(app):        # run startup/shutdown by hand
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            print(f"Each fake call waits {slow_io.DELAY} s. {REQUESTS} requests are sent at the same time.\n")
            for label, path in [
                ("async def + await asyncio.sleep", "/demo/non-blocking"),
                ("def + time.sleep (thread pool)", "/demo/threadpool"),
                ("async def + time.sleep (blocks!)", "/demo/blocking"),
            ]:
                print(f"{label:<36}{await measure(client, path, REQUESTS):5.2f} s")

            print("\nOne request that needs two independent slow calls:\n")
            print(f"{'one await after the other':<36}{await measure(client, '/orders/1001/overview-sequential', 1):5.2f} s")
            print(f"{'asyncio.gather (both at once)':<36}{await measure(client, '/orders/1001/overview', 1):5.2f} s")


if __name__ == "__main__":
    asyncio.run(main())
