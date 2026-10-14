"""Simple tests for the Orders API. Run them with:  pytest"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    # "with" runs the lifespan, so every test starts from the seeded data.
    with TestClient(app) as client:
        yield client


NEW_ORDER = {
    "customer": "Maria Verdi",
    "orderDate": "2026-03-01",
    "lines": [{"sku": "PEN-1", "quantity": 4, "unit_price": 2.5}],
}


def test_root(client):
    assert client.get("/").json() == {"message": "Orders API"}


def test_list_orders_returns_summaries_without_lines(client):
    orders = client.get("/orders").json()
    assert len(orders) == 2
    assert "lines" not in orders[0]
    assert orders[0]["line_count"] == 2 and orders[0]["total_amount"] == 54.5


def test_filter_by_status_and_paging(client):
    assert [o["customer"] for o in client.get("/orders?status=paid").json()] == ["Anna Rossi"]
    assert len(client.get("/orders?limit=1").json()) == 1
    assert client.get("/orders?limit=0").status_code == 422      # limit must be >= 1


def test_get_order_and_its_lines(client):
    assert client.get("/orders/1001").json()["customer"] == "Anna Rossi"
    assert len(client.get("/orders/1001/lines").json()) == 2


def test_unknown_order_is_404_and_bad_id_is_422(client):
    assert client.get("/orders/9999").status_code == 404
    assert client.get("/orders/abc").status_code == 422


def test_create_order_uses_the_alias_and_runs_the_background_task(client):
    response = client.post("/orders", json=NEW_ORDER)
    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 1003 and body["orderDate"] == "2026-03-01" and body["total_amount"] == 10.0
    assert app.state.outbox == ["confirmation for order 1003"]


def test_create_order_with_invalid_body_is_422(client):
    assert client.post("/orders", json={"customer": ""}).status_code == 422
    bad_line = {"customer": "X", "lines": [{"sku": "A", "quantity": 0, "unit_price": 1}]}
    assert client.post("/orders", json=bad_line).status_code == 422


def test_put_replaces_the_order(client):
    response = client.put("/orders/1002", json=NEW_ORDER)
    assert response.status_code == 200
    assert response.json()["customer"] == "Maria Verdi" and response.json()["id"] == 1002


def test_patch_changes_only_the_sent_fields(client):
    response = client.patch("/orders/1002", json={"status": "shipped"})
    assert response.json()["status"] == "shipped"
    assert response.json()["customer"] == "Luca Bianchi"          # untouched


def test_delete_removes_the_order(client):
    assert client.delete("/orders/1002").status_code == 204
    assert client.get("/orders/1002").status_code == 404
