"""Background tasks can be async too."""

import asyncio


async def send_confirmation(outbox: list, order_id: int) -> None:
    """Pretend to send a confirmation e-mail, after the response has been sent.

    FastAPI runs an "async def" background task on the event loop and a plain
    "def" background task in a thread pool. Either way the client does not wait.
    """
    await asyncio.sleep(0.01)             # stands for: await mail_client.send(...)
    outbox.append(f"confirmation for order {order_id}")
