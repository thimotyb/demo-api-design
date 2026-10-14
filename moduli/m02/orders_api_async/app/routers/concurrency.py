"""Three endpoints that wait DELAY seconds in three different ways.

Call each one with several requests at the same time (see tests/test_concurrency.py
or timing_demo.py) and compare the total time:

  /demo/non-blocking  async def + await asyncio.sleep   -> requests overlap     (GOOD)
  /demo/threadpool    def       + time.sleep            -> requests overlap     (OK)
  /demo/blocking      async def + time.sleep            -> requests queue up    (BAD)
"""

import asyncio
import time

from fastapi import APIRouter

from app import slow_io

router = APIRouter(prefix="/demo", tags=["Concurrency demo"])


@router.get("/non-blocking")
async def non_blocking():
    # "await" hands control back to the event loop while we wait,
    # so other requests are served during these seconds.
    await asyncio.sleep(slow_io.DELAY)
    return {"kind": "async + await"}


@router.get("/threadpool")
def threadpool():
    # A plain "def" operation is run by FastAPI in a thread pool.
    # time.sleep() blocks only that thread, so other requests are not delayed.
    time.sleep(slow_io.DELAY)
    return {"kind": "def in a thread"}


@router.get("/blocking")
async def blocking():
    # MISTAKE: time.sleep() is a blocking call, and here it runs ON the event loop.
    # Nothing else can run until it returns: all requests wait in line.
    # Never call blocking code (time.sleep, requests.get, a sync database driver)
    # inside "async def". Use "def", or an async library, instead.
    time.sleep(slow_io.DELAY)
    return {"kind": "async def with blocking code"}
