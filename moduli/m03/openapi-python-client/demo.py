from __future__ import annotations

import json
import os

import requests

from m3_orders_api_demo_client import Client, OrderCreate, OrderLineBase, create_order, get_order, list_order_lines, list_orders


TOKEN_URL = os.getenv("TOKEN_URL", "http://localhost:8080/realms/m3-jwt/protocol/openid-connect/token")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8001")
CLIENT_ID = os.getenv("CLIENT_ID", "m3-fastapi-client")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "m3-fastapi-secret")


def get_token() -> str:
    response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def main() -> int:
    client = Client(base_url=API_BASE_URL, token=get_token())

    orders = list_orders(client)
    print("Current orders:")
    print(json.dumps(orders, indent=2, ensure_ascii=False))

    if orders:
        first_order_id = orders[0]["id"]
        print(f"\nOrder {first_order_id} detail:")
        print(json.dumps(get_order(client, first_order_id), indent=2, ensure_ascii=False))
        print(f"\nOrder {first_order_id} lines:")
        print(json.dumps(list_order_lines(client, first_order_id), indent=2, ensure_ascii=False))

    created = create_order(
        client,
        OrderCreate(
            customer="Gamma Srl",
            status="new",
            lines=[
                OrderLineBase(sku="MOUSE-001", description="Wireless mouse", quantity=4, unit_price=18.5),
                OrderLineBase(sku="PAD-002", description="Mouse pad", quantity=4, unit_price=4.25),
            ],
        ),
    )
    print("\nCreated order:")
    print(json.dumps(created, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

