"""Fake slow input/output, so the effect of async is easy to see.

A real API spends most of its time WAITING: for a database, another service, a
file. Here asyncio.sleep() stands for that waiting.

  await asyncio.sleep(x)  -> waits x seconds but lets the server handle other
                             requests in the meantime (non-blocking).
  time.sleep(x)           -> waits x seconds and freezes everything (blocking).
"""

import asyncio

# How long each fake call takes, in seconds. Tests change this to run faster.
DELAY = 0.2


async def database_call() -> None:
    """Stands for something like:  row = await db.fetch_one(...)"""
    await asyncio.sleep(DELAY)


async def shipping_service_call() -> dict:
    """Stands for something like:  response = await http_client.get(shipping_url)"""
    await asyncio.sleep(DELAY)
    return {"estimated_days": 3}
