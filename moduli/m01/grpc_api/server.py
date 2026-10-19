"""Shipment service over gRPC (grpc.aio) on top of the shared domain."""

from __future__ import annotations

import asyncio
import os

import grpc
from grpc_reflection.v1alpha import reflection

import grpc_api  # noqa: F401  (puts the generated code on sys.path)
from checkout.v1 import checkout_pb2 as pb
from checkout.v1 import checkout_pb2_grpc as pb_grpc
from shared.domain import DomainError, InvalidRequest, ShipmentNotFound, Shipment, ShipmentEvent, Store

# The same domain codes, mapped to gRPC status codes.
STATUS = {
    InvalidRequest: grpc.StatusCode.INVALID_ARGUMENT,
    ShipmentNotFound: grpc.StatusCode.NOT_FOUND,
}
SLOW_TRACKING_CODE = "TRK-SLOW"


def _status(name: str) -> int:
    return pb.ShipmentStatus.Value(name)


def _event(e: ShipmentEvent) -> pb.ShipmentEvent:
    return pb.ShipmentEvent(status=_status(e.status), location=e.location, occurred_at=e.occurred_at.isoformat())


def _shipment(s: Shipment) -> pb.Shipment:
    return pb.Shipment(tracking_code=s.tracking_code, carrier=s.carrier, status=_status(s.status),
                       events=[_event(e) for e in s.events])


class ShipmentService(pb_grpc.ShipmentServiceServicer):
    def __init__(self, store: Store, stream_interval: float = 0.05, slow_lookup: float = 2.0) -> None:
        self.store = store
        self.stream_interval = stream_interval
        self.slow_lookup = slow_lookup

    async def _abort(self, context: grpc.aio.ServicerContext, error: DomainError):
        # The stable domain code travels as trailing metadata next to the gRPC status.
        context.set_trailing_metadata((("x-error-code", error.code),))
        await context.abort(STATUS.get(type(error), grpc.StatusCode.INTERNAL), error.message)

    async def GetShipment(self, request, context):
        # Metadata is the gRPC counterpart of HTTP headers: echo the correlation id.
        metadata = dict(context.invocation_metadata())
        if "x-request-id" in metadata:
            context.set_trailing_metadata((("x-request-id", metadata["x-request-id"]),))
        if request.tracking_code == SLOW_TRACKING_CODE:
            await asyncio.sleep(self.slow_lookup)  # a slow carrier; the client deadline cancels the call
        try:
            return _shipment(self.store.get_shipment(request.tracking_code))
        except DomainError as error:
            await self._abort(context, error)

    async def TrackShipment(self, request, context):
        try:
            shipment = self.store.get_shipment(request.tracking_code)
            future = self.store.future_events(request.tracking_code)
        except DomainError as error:
            await self._abort(context, error)
        for event in shipment.events:
            yield _event(event)
        for event in future:
            await asyncio.sleep(self.stream_interval)
            yield _event(event)


async def start_server(store: Store | None = None, address: str = "127.0.0.1:0", **options) -> tuple[grpc.aio.Server, int]:
    server = grpc.aio.server()
    pb_grpc.add_ShipmentServiceServicer_to_server(ShipmentService(store or Store(), **options), server)
    # Reflection lets generic clients (grpcurl, grpcui, Postman) list the services and call them without the .proto file.
    reflection.enable_server_reflection(
        (pb.DESCRIPTOR.services_by_name["ShipmentService"].full_name, reflection.SERVICE_NAME), server)
    port = server.add_insecure_port(address)
    await server.start()
    return server, port


async def main() -> None:
    # A visible pause between live updates, so a client such as Postman shows them one by one.
    # SHIPMENT_STREAM_INTERVAL (seconds) changes it; the tests use their own, shorter interval.
    interval = float(os.environ.get("SHIPMENT_STREAM_INTERVAL", "1.0"))
    server, port = await start_server(address="127.0.0.1:50051", stream_interval=interval)
    print(f"ShipmentService listening on 127.0.0.1:{port}", flush=True)
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(main())
