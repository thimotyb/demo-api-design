import httpx
import pytest

from app.main import PRODUCTS, app


@pytest.fixture
async def client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c


# A GET carries a validator (ETag) and the caching rules (Cache-Control).
async def test_a_product_has_an_etag_and_a_cache_control(client):
    response = await client.get("/products/1")
    assert response.status_code == 200
    assert response.headers["ETag"].startswith('"')
    assert response.headers["Cache-Control"] == "public, max-age=60"


# The client repeats the ETag in If-None-Match and gets 304 with no body: the copy it holds is current.
async def test_a_matching_if_none_match_gets_304_without_a_body(client):
    first = await client.get("/products/1")
    second = await client.get("/products/1", headers={"If-None-Match": first.headers["ETag"]})
    assert second.status_code == 304
    assert second.content == b""
    assert second.headers["ETag"] == first.headers["ETag"]
    assert second.headers["Cache-Control"] == "public, max-age=60"


# After the product changes, the old ETag no longer matches: the client receives the new body and a new ETag.
async def test_a_changed_product_has_a_new_etag_and_the_old_one_does_not_match(client):
    old = await client.get("/products/2")
    await client.put("/products/2/price", json={"price": "12.00"})
    try:
        new = await client.get("/products/2", headers={"If-None-Match": old.headers["ETag"]})
        assert new.status_code == 200
        assert new.json()["price"] == "12.00"
        assert new.headers["ETag"] != old.headers["ETag"]
    finally:
        PRODUCTS["2"]["price"] = "10.00"


# A weak validator, a list of validators and * are all accepted forms of If-None-Match.
@pytest.mark.parametrize("form", ['W/{etag}', '"other", {etag}', "*"])
async def test_if_none_match_accepts_weak_lists_and_star(client, form):
    etag = (await client.get("/products/1")).headers["ETag"]
    response = await client.get("/products/1", headers={"If-None-Match": form.format(etag=etag)})
    assert response.status_code == 304


async def test_an_unknown_product_is_404(client):
    assert (await client.get("/products/nope")).status_code == 404
