"""Field-level policies for the GraphQL API: caching and cost-based rate limiting.

A GraphQL server has one URL and one HTTP method for every operation, so an
HTTP cache or a per-route rate limit cannot tell a cheap query from an expensive
one. The policies therefore live inside the GraphQL layer:

* CachedField caches the result of one field's resolver (here: the carrier lookup).
* QueryCostLimiter prices a query from its fields before executing it and spends
  a per-client budget (token bucket).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from graphql import (FieldNode, FragmentSpreadNode, GraphQLError, GraphQLObjectType, InlineFragmentNode,
                     OperationDefinitionNode, SelectionSetNode, get_named_type, is_composite_type)
from strawberry.extensions import FieldExtension, SchemaExtension

Clock = Callable[[], float]
_MISSING = object()


# --- Field-level cache -------------------------------------------------------

@dataclass
class FieldCache:
    """TTL cache shared by the fields that opt in. The clock is injectable for tests."""
    clock: Clock = time.monotonic
    _entries: dict[tuple, tuple[float, Any]] = field(default_factory=dict)

    def get(self, key: tuple) -> Any:
        entry = self._entries.get(key)
        if entry is None or entry[0] <= self.clock():
            self._entries.pop(key, None)
            return _MISSING
        return entry[1]

    def set(self, key: tuple, value: Any, ttl: float) -> None:
        self._entries[key] = (self.clock() + ttl, value)


class CachedField(FieldExtension):
    """Cache one field's resolver result for `ttl` seconds.

    `key` selects what makes two calls equivalent. Cache only data that does not
    depend on who is asking: a key without the user must never hold personal data.
    """

    def __init__(self, ttl: float, key: Callable[[Any, dict], Any]) -> None:
        self.ttl = ttl
        self.key = key

    def resolve(self, next_, source, info, **kwargs):
        cache: FieldCache = info.context["cache"]
        key = (info._raw_info.parent_type.name, info.field_name, self.key(source, kwargs))
        hit = cache.get(key)
        if hit is not _MISSING:
            return hit
        value = next_(source, info, **kwargs)
        cache.set(key, value, self.ttl)
        return value


# --- Cost-based rate limiting -------------------------------------------------

# Cost in points per field, "Type.field". Unlisted object fields cost 1, scalars cost 0.
# The costs follow the work behind a field: the shipment field calls the carrier.
COSTS = {
    "Query.order": 1,
    "Order.shipment": 5,
    "Order.customer": 2,
    "Order.lines": 2,
    "Shipment.events": 3,
}


def query_cost(operation: OperationDefinitionNode, document, schema, costs: dict[str, int] = COSTS) -> int:
    """Sum the cost of every field in the operation, following fragments."""
    fragments = {d.name.value: d for d in document.definitions if d.kind == "fragment_definition"}
    root = schema.query_type if operation.operation.value == "query" else schema.mutation_type

    def walk(selection_set: SelectionSetNode | None, parent: GraphQLObjectType) -> int:
        total = 0
        for node in (selection_set.selections if selection_set else ()):
            if isinstance(node, FieldNode):
                if node.name.value.startswith("__"):
                    continue
                definition = parent.fields[node.name.value]
                named = get_named_type(definition.type)
                total += costs.get(f"{parent.name}.{node.name.value}", 1 if is_composite_type(named) else 0)
                if is_composite_type(named):
                    total += walk(node.selection_set, named)
            elif isinstance(node, FragmentSpreadNode):
                fragment = fragments[node.name.value]
                total += walk(fragment.selection_set, schema.get_type(fragment.type_condition.name.value))
            elif isinstance(node, InlineFragmentNode):
                target = schema.get_type(node.type_condition.name.value) if node.type_condition else parent
                total += walk(node.selection_set, target)
        return total

    return walk(operation.selection_set, root)


@dataclass
class _Bucket:
    points: float
    updated: float


@dataclass
class QueryCostLimiter:
    """Token bucket per client: `capacity` points, refilled at `refill_per_second`."""
    capacity: float = 20
    refill_per_second: float = 10
    clock: Clock = time.monotonic
    _buckets: dict[str, _Bucket] = field(default_factory=dict)

    def spend(self, client: str, cost: float) -> tuple[bool, float, float]:
        """Return (allowed, remaining points, seconds until the cost is affordable)."""
        now = self.clock()
        bucket = self._buckets.setdefault(client, _Bucket(self.capacity, now))
        bucket.points = min(self.capacity, bucket.points + (now - bucket.updated) * self.refill_per_second)
        bucket.updated = now
        if cost <= bucket.points:
            bucket.points -= cost
            return True, bucket.points, 0.0
        return False, bucket.points, (cost - bucket.points) / self.refill_per_second


class RateLimitExtension(SchemaExtension):
    """Price the operation before executing it; refuse it when the client's budget is spent."""

    def on_execute(self):
        ctx = self.execution_context
        limiter: QueryCostLimiter = ctx.context["limiter"]
        operation = next(d for d in ctx.graphql_document.definitions
                         if isinstance(d, OperationDefinitionNode)
                         and (ctx.operation_name in (None, d.name.value if d.name else None)))
        cost = query_cost(operation, ctx.graphql_document, ctx.schema._schema)
        allowed, remaining, retry_after = limiter.spend(ctx.context["client"], cost)
        if not allowed:
            # A policy decision belongs to the transport: answer 429 with Retry-After,
            # and still give GraphQL clients a coded error in the body.
            response = ctx.context["response"]
            response.status_code = 429
            response.headers["Retry-After"] = str(max(1, round(retry_after)))
            raise GraphQLError("Query budget exhausted; retry later.", extensions={
                "code": "RATE_LIMITED", "cost": cost, "remaining": round(remaining, 2),
                "retryAfterSeconds": round(retry_after, 2)})
        yield
