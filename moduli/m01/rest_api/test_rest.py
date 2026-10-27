import pytest
from fastapi.testclient import TestClient

from rest_api.app import create_app
from shared.domain import Store

PAYMENT = {"customer_id": "c-001", "amount": {"amount": "19.90", "currency": "EUR"}, "payment_token": "tok_demo_visa"}


@pytest.fixture
def store():
    return Store()


@pytest.fixture
def client(store):
    return TestClient(create_app(store))


# GET /v1/orders/{id} returns the whole order (status, totals, all lines) in one REST resource.
def test_get_order_returns_the_full_representation(client):
    body = client.get("/v1/orders/o-1001").json()
    assert body["status"] == "SHIPPED"
    assert body["total_amount"] == "64.50" and body["currency"] == "EUR"
    assert len(body["lines"]) == 3


# In REST the shipment is a different resource: the client needs a second request to GET /orders/{id}/shipment.
def test_shipment_is_a_separate_request(client):
    body = client.get("/v1/orders/o-1001/shipment").json()
    assert body["tracking_code"] == "TRK-1001"
    assert body["status"] == "IN_TRANSIT"


# A missing order gives HTTP 404 and the error body shared by all styles (a stable `code` field).
def test_unknown_order_is_404_with_the_shared_error_shape(client):
    response = client.get("/v1/orders/nope")
    assert response.status_code == 404
    assert response.json()["code"] == "ORDER_NOT_FOUND"


# An invalid payment (negative amount) is mapped to 400 INVALID_REQUEST instead of FastAPI's default 422.
def test_validation_failure_is_400_not_fastapi_default_422(client):
    response = client.post("/v1/payments", json={**PAYMENT, "amount": {"amount": "-1", "currency": "EUR"}})
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_REQUEST"


# Idempotency: the same Idempotency-Key sent twice creates one payment; the second call is a replay (200, same id, no new gateway call).
def test_payment_created_then_replayed_with_the_same_key(client, store):
    first = client.post("/v1/payments", json=PAYMENT, headers={"Idempotency-Key": "k-1"})
    second = client.post("/v1/payments", json=PAYMENT, headers={"Idempotency-Key": "k-1"})
    assert first.status_code == 201
    assert second.status_code == 200 and second.headers["Idempotent-Replayed"] == "true"
    assert second.json()["id"] == first.json()["id"]
    assert store.gateway.calls == 1
    assert len([p for p in store.payments if p != "p-0000"]) == 1


# Without an Idempotency-Key there is no protection: two identical POSTs create two payments.
def test_without_a_key_every_post_creates_a_payment(client, store):
    client.post("/v1/payments", json=PAYMENT)
    client.post("/v1/payments", json=PAYMENT)
    assert len([p for p in store.payments if p != "p-0000"]) == 2


# Reusing a key with a different body is a client bug, so the API answers 409 IDEMPOTENCY_CONFLICT.
def test_same_key_with_a_different_request_is_a_conflict(client):
    client.post("/v1/payments", json=PAYMENT, headers={"Idempotency-Key": "k-2"})
    other = {**PAYMENT, "amount": {"amount": "25.00", "currency": "EUR"}}
    response = client.post("/v1/payments", json=other, headers={"Idempotency-Key": "k-2"})
    assert response.status_code == 409
    assert response.json()["code"] == "IDEMPOTENCY_CONFLICT"


# A temporary gateway failure (402) is not stored against the key, so a retry with the same key succeeds (201) and creates only one payment.
def test_transient_failure_can_be_retried_with_the_same_key(client, store):
    flaky = {**PAYMENT, "payment_token": "tok_flaky"}
    first = client.post("/v1/payments", json=flaky, headers={"Idempotency-Key": "k-3"})
    second = client.post("/v1/payments", json=flaky, headers={"Idempotency-Key": "k-3"})
    assert first.status_code == 402 and first.json()["code"] == "TRANSIENT_GATEWAY_FAILURE"
    assert second.status_code == 201
    assert store.gateway.calls == 2
    assert len([p for p in store.payments if p != "p-0000"]) == 1


# A definitive refusal (card declined) is stored: the retry gets the same 402 back without calling the gateway again.
def test_declined_payment_is_not_retried_and_replays_the_refusal(client, store):
    declined = {**PAYMENT, "payment_token": "tok_declined"}
    first = client.post("/v1/payments", json=declined, headers={"Idempotency-Key": "k-4"})
    second = client.post("/v1/payments", json=declined, headers={"Idempotency-Key": "k-4"})
    assert first.status_code == second.status_code == 402
    assert first.json()["code"] == second.json()["code"] == "PAYMENT_DECLINED"
    assert store.gateway.calls == 1


# Versioning: /v2 exposes a new order shape (`total` as an object) while /v1 keeps the old one for existing clients.
def test_v2_changes_the_order_shape_and_v1_is_unchanged(client):
    v1 = client.get("/v1/orders/o-1001").json()
    v2 = client.get("/v2/orders/o-1001").json()
    assert "total_amount" in v1 and "total" not in v1
    assert v2["total"] == {"amount": "64.50", "currency": "EUR"}
    assert "total_amount" not in v2


# REST can use plain HTTP caching: the shipment response carries a Cache-Control header, so no custom cache is needed.
def test_shipment_response_is_cacheable_by_http_alone(client):
    response = client.get("/v1/orders/o-1001/shipment")
    # "private": only the end user's own cache (their browser) may store this response.
    # Shared caches such as a CDN or a proxy must not, because the content can be
    # specific to the user. "max-age=30": the stored copy is fresh for 30 seconds.
    assert response.headers["Cache-Control"] == "private, max-age=30"


# The error body always has code, message and details; a validation failure names the offending field.
def test_error_body_has_code_message_and_details(client):
    response = client.post("/v1/payments", json={**PAYMENT, "amount": {"amount": "-1", "currency": "EUR"}})
    body = response.json()
    assert response.status_code == 400 and body["code"] == "INVALID_REQUEST"
    assert body["details"]["field"].endswith("amount.amount")


# Retries on one key are bounded: two transient failures say how many attempts were used, the third is final and replayed.
def test_third_transient_failure_becomes_retries_exhausted(client, store):
    outage = {**PAYMENT, "payment_token": "tok_transient"}
    headers = {"Idempotency-Key": "k-5"}
    answers = [client.post("/v1/payments", json=outage, headers=headers) for _ in range(4)]
    assert [a.status_code for a in answers] == [402, 402, 402, 402]
    assert [a.json()["code"] for a in answers] == ["TRANSIENT_GATEWAY_FAILURE"] * 2 + ["RETRIES_EXHAUSTED"] * 2
    assert answers[0].json()["details"] == {"attempt": 1, "max_attempts": 3}
    assert answers[2].json()["details"] == {"attempts": 3}
    assert store.gateway.calls == 3
