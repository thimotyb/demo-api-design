from __future__ import annotations

from typing import Any

from .client import Client
from .models import OrderCreate


def get_root(client: Client) -> dict[str, Any]:
    return client.request("GET", "/")


def list_orders(client: Client) -> list[dict[str, Any]]:
    return client.request("GET", "/orders")


def get_order(client: Client, order_id: int) -> dict[str, Any]:
    return client.request("GET", f"/orders/{order_id}")


def list_order_lines(client: Client, order_id: int) -> list[dict[str, Any]]:
    return client.request("GET", f"/orders/{order_id}/lines")


def create_order(client: Client, order: OrderCreate | dict[str, Any]) -> dict[str, Any]:
    payload = order.to_dict() if isinstance(order, OrderCreate) else order
    return client.request("POST", "/orders", json=payload)

