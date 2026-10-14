import grpc
import pytest

import grpc_api  # noqa: F401
from checkout.v1 import checkout_pb2 as pb
from checkout.v1 import checkout_pb2_grpc as pb_grpc
from grpc_api.server import start_server
from shared.domain import Store


@pytest.fixture
async def stub():
    server, port = await start_server(Store(), stream_interval=0.001, slow_lookup=2.0)
    channel = grpc.aio.insecure_channel(f"127.0.0.1:{port}")
    yield pb_grpc.ShipmentServiceStub(channel)
    await channel.close()
    await server.stop(None)


async def test_unary_call_returns_the_shipment(stub):
    shipment = await stub.GetShipment(pb.GetShipmentRequest(tracking_code="TRK-1001"))
    assert shipment.carrier == "Example Carrier"
    assert shipment.status == pb.IN_TRANSIT
    assert [e.location for e in shipment.events] == ["Milano depot", "Bologna hub"]


async def test_unknown_shipment_is_not_found_with_the_domain_code(stub):
    with pytest.raises(grpc.aio.AioRpcError) as error:
        await stub.GetShipment(pb.GetShipmentRequest(tracking_code="TRK-9999"))
    assert error.value.code() == grpc.StatusCode.NOT_FOUND
    assert dict(error.value.trailing_metadata())["x-error-code"] == "SHIPMENT_NOT_FOUND"


async def test_malformed_tracking_code_is_invalid_argument(stub):
    with pytest.raises(grpc.aio.AioRpcError) as error:
        await stub.GetShipment(pb.GetShipmentRequest(tracking_code="bad code"))
    assert error.value.code() == grpc.StatusCode.INVALID_ARGUMENT


async def test_deadline_cancels_a_slow_call(stub):
    with pytest.raises(grpc.aio.AioRpcError) as error:
        await stub.GetShipment(pb.GetShipmentRequest(tracking_code="TRK-SLOW"), timeout=0.2)
    assert error.value.code() == grpc.StatusCode.DEADLINE_EXCEEDED


async def test_metadata_travels_with_the_call(stub):
    call = stub.GetShipment(pb.GetShipmentRequest(tracking_code="TRK-1001"), metadata=(("x-request-id", "req-42"),))
    await call
    assert dict(await call.trailing_metadata())["x-request-id"] == "req-42"


async def test_server_streaming_sends_history_then_live_updates_until_delivered(stub):
    events = [e async for e in stub.TrackShipment(pb.TrackShipmentRequest(tracking_code="TRK-1001"))]
    assert [pb.ShipmentStatus.Name(e.status) for e in events] == [
        "CREATED", "IN_TRANSIT", "IN_TRANSIT", "IN_TRANSIT", "DELIVERED"]
    assert events[-1].location == "Customer address"


async def test_stream_for_an_unknown_shipment_fails_with_not_found(stub):
    with pytest.raises(grpc.aio.AioRpcError) as error:
        async for _ in stub.TrackShipment(pb.TrackShipmentRequest(tracking_code="TRK-9999")):
            pass
    assert error.value.code() == grpc.StatusCode.NOT_FOUND


async def test_old_message_without_the_new_field_still_parses(stub):
    # Compatible evolution: bytes written before field 5 existed are still valid.
    old = pb.Shipment(tracking_code="TRK-1001", carrier="X", status=pb.CREATED)
    parsed = pb.Shipment.FromString(old.SerializeToString())
    assert parsed.estimated_delivery == ""
