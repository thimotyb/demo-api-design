"""One GraphQL request must become one trace that crosses into the REST API.

The REST API runs in a real uvicorn server on a free port, because the trace context travels
in the `traceparent` header of a real HTTP request. Spans are collected in memory, so the test
does not need Jaeger or Docker.
"""

import socket
import threading
import time

import pytest
import uvicorn
from fastapi.testclient import TestClient
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind, StatusCode

from graphql_api.app import create_app as create_graphql, rest_client
from rest_api.app import create_app as create_rest
from shared.domain import Store


@pytest.fixture(scope="module")
def spans():
    return InMemorySpanExporter()


@pytest.fixture(scope="module")
def graphql(spans):
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(spans))

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    rest_app = create_rest(Store())
    FastAPIInstrumentor.instrument_app(rest_app, tracer_provider=provider)
    server = uvicorn.Server(uvicorn.Config(rest_app, port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.01)

    HTTPXClientInstrumentor().instrument(tracer_provider=provider)
    graphql_app = create_graphql(rest_client(base_url=f"http://127.0.0.1:{port}"))
    FastAPIInstrumentor.instrument_app(graphql_app, tracer_provider=provider)
    with TestClient(graphql_app) as client:
        yield client

    HTTPXClientInstrumentor().uninstrument()
    server.should_exit = True
    thread.join(timeout=5)


def finished(spans, expected_rest_calls=0):
    """The finished spans. The REST server span ends just after its response is sent, so wait for it."""
    deadline = time.monotonic() + 2
    while True:
        found = spans.get_finished_spans()
        rest = [s for s in found if s.kind == SpanKind.SERVER and s.attributes["http.target"] != "/graphql"]
        if len(rest) >= expected_rest_calls or time.monotonic() > deadline:
            return found
        time.sleep(0.01)


def ask(client, query):
    response = client.post("/graphql", json={"query": query})
    assert response.status_code == 200
    return response.json()


# Each REST server span is a child of an HTTP client span of the GraphQL API, in the same trace.
def test_a_graphql_request_is_one_trace_across_both_apis(graphql, spans):
    spans.clear()
    body = ask(graphql, '{ order(id: "o-1001") { id customer { email } shipment { status } } }')
    assert "errors" not in body

    all_spans = finished(spans, expected_rest_calls=3)
    by_id = {s.context.span_id: s for s in all_spans}
    servers = [s for s in all_spans if s.kind == SpanKind.SERVER]
    graphql_root = next(s for s in servers if s.attributes["http.target"] == "/graphql")
    rest_calls = [s for s in servers if s is not graphql_root]

    assert len(rest_calls) == 3  # the order, its customer and its shipment
    for call in rest_calls:
        assert call.context.trace_id == graphql_root.context.trace_id
        assert by_id[call.parent.span_id].kind == SpanKind.CLIENT  # the httpx call of the GraphQL API


# A refusal from the REST API (402) marks the HTTP client span of the GraphQL API as an error, not the REST server span.
def test_a_refused_payment_marks_the_client_span_as_an_error(graphql, spans):
    spans.clear()
    ask(graphql, 'mutation { authorizePayment(input: {customerId: "c-001", amount: {amount: "19.90", currency: "EUR"},'
                 ' paymentToken: "tok_declined"}) { id } }')
    client_spans = [s for s in finished(spans, expected_rest_calls=1) if s.kind == SpanKind.CLIENT]
    assert client_spans and client_spans[0].status.status_code == StatusCode.ERROR
    # The REST server span of a 4xx answer is not an error: the server did what the contract says.
    rest_server = [s for s in finished(spans) if s.kind == SpanKind.SERVER and s.attributes["http.target"] != "/graphql"]
    assert rest_server and rest_server[0].status.status_code != StatusCode.ERROR
