"""Client for the shipment service. Run the server first: python -m grpc_api.server"""

from __future__ import annotations

import asyncio
import sys

import grpc

# Importing grpc_api has a side effect: it generates the protobuf code if missing and
# adds it to sys.path. It must come before the `checkout.v1` imports below, which
# is why the import looks unused (noqa: F401).
import grpc_api  # noqa: F401
# pb: the message classes (requests, responses, enums) generated from the .proto file.
from checkout.v1 import checkout_pb2 as pb
# pb_grpc: the generated client "stub" and server base classes for the service.
from checkout.v1 import checkout_pb2_grpc as pb_grpc


async def main(tracking_code: str = "TRK-1001", target: str = "127.0.0.1:50051") -> None:
    # A channel is the long-lived HTTP/2 connection to the server. "insecure" means
    # no TLS, fine for a local demo. `async with` closes the channel on exit.
    async with grpc.aio.insecure_channel(target) as channel:
        # The stub is the client-side object: calling its methods sends the RPCs.
        stub = pb_grpc.ShipmentServiceStub(channel)

        # 1) Unary RPC: one request, one response. Calling a method looks like a
        #    local async function call, but it goes over the network.
        shipment = await stub.GetShipment(
            pb.GetShipmentRequest(tracking_code=tracking_code),
            timeout=1.0,                              # deadline in seconds: fail with DEADLINE_EXCEEDED if slower
            metadata=(("x-request-id", "demo-1"),),   # like HTTP headers; here, an id to correlate logs
        )
        # Enums arrive as integers; .Name() turns the value into its label (e.g. IN_TRANSIT).
        print(f"{shipment.tracking_code} {pb.ShipmentStatus.Name(shipment.status)} via {shipment.carrier}")

        # 2) Server-streaming RPC: one request, many responses. The server sends the
        #    shipment history first, then live updates, and ends the stream when the
        #    shipment is delivered. `async for` receives each event as it arrives.
        print("streaming updates:")
        async for event in stub.TrackShipment(pb.TrackShipmentRequest(tracking_code=tracking_code)):
            print(f"  {pb.ShipmentStatus.Name(event.status):<11} {event.location}")


if __name__ == "__main__":
    # Optional command-line arguments are passed to main(): tracking_code, then target.
    asyncio.run(main(*sys.argv[1:]))
