"""Work that runs *after* the response has been sent (background tasks)."""


def send_confirmation(outbox: list, order_id: int) -> None:
    """Pretend to send a confirmation e-mail.

    The client does not wait for this function: FastAPI calls it once the
    response is on its way. Here we only append a line to a list, so the example
    needs no mail server and the result is easy to check.

    Background tasks run in the same process. If the server stops, they are lost.
    Use a queue and a worker for work that must never be lost.
    """
    outbox.append(f"confirmation for order {order_id}")
