import os
import json
import sys

import requests


# Default values used when the example is run locally without extra env vars.
TOKEN_URL = os.getenv(
    "TOKEN_URL",
    "http://localhost:8080/realms/m3-jwt/protocol/openid-connect/token",
)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8001")
CLIENT_ID = os.getenv("CLIENT_ID", "m3-fastapi-client")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "m3-fastapi-secret")


def get_token() -> str:
    # OAuth2 client_credentials: ask Keycloak for an access token using the client id and secret.
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
    data = response.json()
    return data["access_token"]


def api_get(access_token: str, path: str) -> dict | list[dict]:
    # Send the token as a Bearer credential to any protected FastAPI endpoint.
    response = requests.get(
        f"{API_BASE_URL}{path}",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def create_order(access_token: str) -> dict:
    # Create a new order with a header and a few rows so the demo shows both read and write flows.
    response = requests.post(
        f"{API_BASE_URL}/orders",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "customer": "Gamma Srl",
            "order_date": "2026-05-18",
            "status": "new",
            "lines": [
                {
                    "sku": "MOUSE-001",
                    "description": "Wireless mouse",
                    "quantity": 4,
                    "unit_price": 18.5,
                },
                {
                    "sku": "PAD-002",
                    "description": "Mouse pad",
                    "quantity": 4,
                    "unit_price": 4.25,
                },
            ],
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def main() -> int:
    # The demo follows a realistic workflow: get a token, inspect the order list, read one order, then create one.
    access_token = get_token()
    orders = api_get(access_token, "/orders")
    print("Current orders:")
    print(json.dumps(orders, indent=2, ensure_ascii=False))

    if orders:
        first_order_id = orders[0]["id"]
        first_order = api_get(access_token, f"/orders/{first_order_id}")
        print(f"\nOrder {first_order_id} detail:")
        print(json.dumps(first_order, indent=2, ensure_ascii=False))

    created_order = create_order(access_token)
    print("\nCreated order:")
    print(json.dumps(created_order, indent=2, ensure_ascii=False))

    created_order_id = created_order["id"]
    created_lines = api_get(access_token, f"/orders/{created_order_id}/lines")
    print(f"\nOrder {created_order_id} lines:")
    print(json.dumps(created_lines, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
