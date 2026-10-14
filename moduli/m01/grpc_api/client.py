"""Client for the shipment service. Run the server first: python -m grpc_api.server"""

from __future__ import annotations

import asyncio
import sys

import grpc

import grpc_api  # noqa: F401
from checkout.v1 import checkout_pb2 as pb
from checkout.v1 import checkout_pb2_grpc as pb_grpc


async def main(tracking_code: str = "TRK-1001", target: str = "127.0.0.1:50051") -> None:
    async with grpc.aio.insecure_channel(target) as channel:
        stub = pb_grpc.ShipmentServiceStub(channel)
        shipment = await stub.GetShipment(pb.GetShipmentRequest(tracking_code=tracking_code), timeout=1.0,
                                          metadata=(("x-request-id", "demo-1"),))
        print(f"{shipment.tracking_code} {pb.ShipmentStatus.Name(shipment.status)} via {shipment.carrier}")
        print("streaming updates:")
        async for event in stub.TrackShipment(pb.TrackShipmentRequest(tracking_code=tracking_code)):
            print(f"  {pb.ShipmentStatus.Name(event.status):<11} {event.location}")


if __name__ == "__main__":
    asyncio.run(main(*sys.argv[1:]))
