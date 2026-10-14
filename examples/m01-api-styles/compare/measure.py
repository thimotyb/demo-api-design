"""Measure the same screens against the REST and GraphQL APIs.

Run: python -m compare.measure
Counts HTTP requests and body bytes (request + response). The numbers come from
in-process calls on synthetic data; they show the shape of the difference, not
production performance.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi.testclient import TestClient

from graphql_api.app import create_app as create_graphql
from rest_api.app import create_app as create_rest
from shared.domain import Store


@dataclass
class Result:
    requests: int
    bytes_sent: int
    bytes_received: int
    data: dict

    @property
    def total(self) -> int:
        return self.bytes_sent + self.bytes_received


# Screen A: order status line. Needs the order status and the last carrier location.
GQL_STATUS = '{ order(id: "o-1001") { status shipment { lastEvent { location } } } }'

# Screen B: order detail. Needs everything the REST representations carry.
GQL_DETAIL = """{ order(id: "o-1001") {
  id status createdAt paymentId totalAmount currency
  lines { sku description quantity unitPrice { amount currency } }
  shipment { trackingCode carrier status events { status location occurredAt } }
} }"""


def rest_status(client: TestClient) -> Result:
    order = client.get("/v1/orders/o-1001")
    shipment = client.get("/v1/orders/o-1001/shipment")
    last = shipment.json()["events"][-1]
    return Result(2, 0, len(order.content) + len(shipment.content),
                  {"status": order.json()["status"], "location": last["location"]})


def graphql_status(client: TestClient) -> Result:
    body = {"query": GQL_STATUS}
    response = client.post("/graphql", json=body)
    order = response.json()["data"]["order"]
    return Result(1, len(response.request.content), len(response.content),
                  {"status": order["status"], "location": order["shipment"]["lastEvent"]["location"]})


def rest_detail(client: TestClient) -> Result:
    order = client.get("/v1/orders/o-1001")
    shipment = client.get("/v1/orders/o-1001/shipment")
    return Result(2, 0, len(order.content) + len(shipment.content),
                  {"status": order.json()["status"], "events": len(shipment.json()["events"])})


def graphql_detail(client: TestClient) -> Result:
    response = client.post("/graphql", json={"query": GQL_DETAIL})
    order = response.json()["data"]["order"]
    return Result(1, len(response.request.content), len(response.content),
                  {"status": order["status"], "events": len(order["shipment"]["events"])})


def measure() -> dict[str, dict[str, Result]]:
    rest, gql = TestClient(create_rest(Store())), TestClient(create_graphql(Store()))
    return {
        "A. status line (2 fields)": {"REST": rest_status(rest), "GraphQL": graphql_status(gql)},
        "B. detail screen (all fields)": {"REST": rest_detail(rest), "GraphQL": graphql_detail(gql)},
    }


def main() -> None:
    print(f"{'screen':<32}{'style':<9}{'requests':>9}{'sent B':>9}{'received B':>12}{'total B':>9}")
    for screen, styles in measure().items():
        for style, r in styles.items():
            print(f"{screen:<32}{style:<9}{r.requests:>9}{r.bytes_sent:>9}{r.bytes_received:>12}{r.total:>9}")


if __name__ == "__main__":
    main()
