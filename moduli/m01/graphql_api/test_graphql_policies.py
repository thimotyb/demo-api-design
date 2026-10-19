"""Field-level caching and cost-based rate limiting (see policies.py)."""

import pytest
from fastapi.testclient import TestClient
from graphql import OperationDefinitionNode, parse

from graphql_api.app import create_app, schema
from graphql_api.policies import query_cost
from shared.domain import Store

CHEAP = '{ order(id: "o-1001") { id status } }'
STATUS_LINE = '{ order(id: "o-1001") { status shipment { lastEvent { location } } } }'
DETAIL = """{ order(id: "o-1001") {
  lines { sku unitPrice { amount } }
  shipment { events { status location } }
} }"""


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def store():
    return Store()


@pytest.fixture
def client(store, clock):
    return TestClient(create_app(store, clock=clock, capacity=20, refill_per_second=10))


def post(client, query, client_id=None):
    headers = {"x-client-id": client_id} if client_id else {}
    return client.post("/graphql", json={"query": query}, headers=headers)


def cost_of(query):
    document = parse(query)
    operation = next(d for d in document.definitions if isinstance(d, OperationDefinitionNode))
    return query_cost(operation, document, schema._schema)


# --- field-level cache --------------------------------------------------------

# Field-level cache: the same query twice calls the carrier only once.
def test_the_carrier_is_called_once_for_repeated_requests(client, store):
    first = post(client, STATUS_LINE).json()
    second = post(client, STATUS_LINE).json()
    assert first == second
    assert store.carrier_lookups == 1


# The cached value expires after its TTL (30 s), so the carrier is called again afterwards.
def test_the_cache_entry_expires_after_its_ttl(client, store, clock):
    post(client, STATUS_LINE)
    clock.now += 31  # ttl is 30 seconds
    post(client, STATUS_LINE)
    assert store.carrier_lookups == 2


# The cache key is the field (tracking code), not the whole query: different selections share one carrier call.
def test_the_cache_is_per_field_not_per_query(client, store):
    # Different selections, same field and same tracking code: one carrier call.
    post(client, '{ order(id: "o-1001") { shipment { status } } }')
    post(client, '{ order(id: "o-1001") { shipment { carrier events { location } } } }')
    assert store.carrier_lookups == 1


# A field without a cache policy (customer) is resolved on every request.
def test_an_uncached_field_is_resolved_every_time(client, store):
    calls = []
    original = store.get_customer
    store.get_customer = lambda cid: (calls.append(cid), original(cid))[1]
    post(client, '{ order(id: "o-1001") { customer { email } } }')
    post(client, '{ order(id: "o-1001") { customer { email } } }')
    assert len(calls) == 2


# --- cost-based rate limiting ---------------------------------------------------

# The query cost is the sum of the weights of the requested fields, so bigger queries cost more.
def test_cost_follows_the_fields_requested():
    assert cost_of(CHEAP) == 1                      # order
    assert cost_of(STATUS_LINE) == 1 + 5 + 1        # order + shipment + lastEvent
    assert cost_of(DETAIL) == 1 + 2 + 1 + 5 + 3     # order + lines + unitPrice + shipment + events


# Fields inside fragments count in the cost too, so fragments cannot be used to hide expensive fields.
def test_fragments_are_priced_too():
    query = '{ order(id: "o-1001") { ...S } } fragment S on Order { shipment { status } }'
    assert cost_of(query) == 1 + 5


# Rate limiting by cost, not by request count: 20 cheap queries pass, while 3 expensive ones exceed the budget.
def test_many_cheap_requests_pass_where_few_expensive_ones_do_not(client):
    # Counting HTTP requests would treat these two groups alike.
    assert all(post(client, CHEAP, "cheap").status_code == 200 for _ in range(20))
    assert post(client, STATUS_LINE, "costly").status_code == 200       # 7 of 20 points
    assert post(client, STATUS_LINE, "costly").status_code == 200       # 14 of 20
    refused = post(client, STATUS_LINE, "costly")                       # would be 21 of 20
    assert refused.status_code == 429


# A refused query gets 429, a RATE_LIMITED error with its cost, and a Retry-After header.
def test_a_refused_query_returns_a_coded_error_and_retry_after(client):
    for _ in range(2):
        post(client, STATUS_LINE)
    refused = post(client, STATUS_LINE)
    body = refused.json()
    assert refused.status_code == 429 and "Retry-After" in refused.headers
    error = body["errors"][0]
    assert error["extensions"]["code"] == "RATE_LIMITED"
    assert error["extensions"]["cost"] == 7
    assert body["data"] is None


# The cost check runs before execution: a refused query does not reach the carrier.
def test_a_refused_query_is_not_executed(client, store):
    post(client, DETAIL)           # 12 points, runs
    lookups = store.carrier_lookups
    post(client, DETAIL)           # 24 > 20 points, refused before execution
    assert store.carrier_lookups == lookups


# The token bucket refills over time: after waiting, a previously refused query is accepted.
def test_the_budget_refills_over_time(client, clock):
    post(client, STATUS_LINE)
    post(client, STATUS_LINE)
    assert post(client, STATUS_LINE).status_code == 429
    clock.now += 1.0               # 10 points per second
    assert post(client, STATUS_LINE).status_code == 200


# Budgets are per client (x-client-id): one client being limited does not affect another.
def test_each_client_has_its_own_budget(client):
    for _ in range(2):
        post(client, STATUS_LINE, "a")
    assert post(client, STATUS_LINE, "a").status_code == 429
    assert post(client, STATUS_LINE, "b").status_code == 200
