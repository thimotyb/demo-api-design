import asyncio

import httpx
import pytest

from app import main


@pytest.fixture
async def client(monkeypatch):
    monkeypatch.setattr(main, "JOB_SECONDS", 0.05)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://test") as c:
        yield c


async def wait_for(client, location, status, attempts=50):
    for _ in range(attempts):
        body = (await client.get(location)).json()
        if body["status"] == status:
            return body
        await asyncio.sleep(0.02)
    raise AssertionError(f"{location} never reached {status}")


# The request is answered at once with 202, a Location to poll and a Retry-After: the slow work has not run yet.
async def test_creating_a_report_answers_202_with_a_location(client):
    response = await client.post("/reports")
    assert response.status_code == 202
    assert response.headers["Location"] == f"/reports/{response.json()['id']}"
    assert response.headers["Retry-After"] == "1"
    assert response.json()["status"] == "queued"


# The status resource says "not done yet" with Retry-After, then returns the result.
async def test_polling_the_status_resource_until_the_report_is_done(client):
    location = (await client.post("/reports")).headers["Location"]
    working = await client.get(location)
    assert working.json()["status"] in ("queued", "running")
    assert working.headers["Retry-After"] == "1"

    done = await wait_for(client, location, "done")
    assert done["result"]["rows"] == 1250
    assert "Retry-After" not in (await client.get(location)).headers


# Slow work does not block the API: while a report runs, another request is answered immediately.
async def test_the_api_stays_responsive_while_a_report_runs(client, monkeypatch):
    monkeypatch.setattr(main, "JOB_SECONDS", 0.5)
    await client.post("/reports")
    assert (await client.get("/products/1")).status_code == 200


async def test_an_unknown_report_is_404(client):
    assert (await client.get("/reports/nope")).status_code == 404
