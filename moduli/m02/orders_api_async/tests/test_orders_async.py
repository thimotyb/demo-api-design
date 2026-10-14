"""The async API behaves exactly like the synchronous one. Run with:  pytest"""

import pytest
from fastapi.testclient import TestClient

from app import slow_io
from app.main import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(slow_io, "DELAY", 0.001)      # no need to wait in functional tests
    with TestClient(app) as client:                   # "with" runs the lifespan (startup/shutdown)
        yield client


def test_root(client):
    assert client.get("/").json() == {"message": "Orders API (async)"}


def test_list_filter_and_get(client):
    assert len(client.get("/orders").json()) == 2
    assert [o["customer"] for o in client.get("/orders?status=paid").json()] == ["Anna Rossi"]
    assert client.get("/orders/1001").json()["line_count"] == 2
    assert len(client.get("/orders/1001/lines").json()) == 2


def test_missing_order_is_404(client):
    assert client.get("/orders/9999").status_code == 404


def test_create_put_patch_delete(client):
    body = {"customer": "Maria Verdi", "orderDate": "2026-03-01",
            "lines": [{"sku": "PEN-1", "quantity": 4, "unit_price": 2.5}]}
    created = client.post("/orders", json=body)
    assert created.status_code == 201 and created.json()["total_amount"] == 10.0
    assert app.state.outbox == ["confirmation for order 1003"]       # async background task ran

    assert client.put("/orders/1003", json={**body, "customer": "M. Verdi"}).json()["customer"] == "M. Verdi"
    assert client.patch("/orders/1003", json={"status": "shipped"}).json()["status"] == "shipped"
    assert client.delete("/orders/1003").status_code == 204
    assert client.get("/orders/1003").status_code == 404


def test_overview_returns_order_and_shipping(client):
    body = client.get("/orders/1001/overview").json()
    assert body == {"order": 1001, "customer": "Anna Rossi", "shipping": {"estimated_days": 3}}
