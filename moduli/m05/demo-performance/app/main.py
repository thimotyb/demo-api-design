"""Performance demo for module M05: HTTP caching and work moved out of the request.

  GET  /products/{id}        ETag + Cache-Control, and 304 Not Modified for a matching If-None-Match
  PUT  /products/{id}/price  changes a product, so its ETag changes
  POST /reports              slow work: answers 202 Accepted with a Location header
  GET  /reports/{id}         the status resource the client polls

The data and the job table are in memory and belong to one process. A real API would use a
database and a queue (a worker process fed by Redis, for example) so that jobs survive a restart
and any instance can answer the polling request.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import uuid

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(title="M05 performance demo")

PRODUCTS = {
    "1": {"id": "1", "name": "API Design handbook", "price": "34.50", "currency": "EUR"},
    "2": {"id": "2", "name": "Coffee mug", "price": "10.00", "currency": "EUR"},
}

# How long the fake report takes, in seconds. The tests make it short.
JOB_SECONDS = 2.0
JOBS: dict[str, dict] = {}
_tasks: set[asyncio.Task] = set()  # keeps a reference to each running job, or it could be garbage collected


# ---------------------------------------------------------------------------
# HTTP caching: ETag, Cache-Control and 304
# ---------------------------------------------------------------------------

def etag_of(body: dict) -> str:
    """A validator for this representation: it changes if and only if the body changes."""
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    return '"' + hashlib.sha256(canonical).hexdigest()[:16] + '"'


def matches(if_none_match: str | None, etag: str) -> bool:
    """True if the client already holds this representation (If-None-Match, weak or strong)."""
    if not if_none_match:
        return False
    candidates = [c.strip().removeprefix("W/") for c in if_none_match.split(",")]
    return "*" in candidates or etag in candidates


@app.get("/products/{product_id}")
def get_product(product_id: str, request: Request):
    product = PRODUCTS.get(product_id)
    if product is None:
        raise HTTPException(404, "Product not found.")
    etag = etag_of(product)
    # public: any cache may store it. max-age: it can be reused for 60 s without asking the server.
    headers = {"ETag": etag, "Cache-Control": "public, max-age=60"}
    if matches(request.headers.get("if-none-match"), etag):
        # The client's copy is current: send the headers and no body. The 304 repeats the
        # validators so the cache can refresh the lifetime of its copy.
        return Response(status_code=304, headers=headers)
    return JSONResponse(product, headers=headers)


class PriceChange(BaseModel):
    price: str = Field(pattern=r"^\d+\.\d{2}$")


@app.put("/products/{product_id}/price")
def change_price(product_id: str, change: PriceChange):
    product = PRODUCTS.get(product_id)
    if product is None:
        raise HTTPException(404, "Product not found.")
    product["price"] = change.price  # the next GET has a different ETag
    return product


# ---------------------------------------------------------------------------
# Slow work: 202 Accepted and a status resource
# ---------------------------------------------------------------------------

async def run_job(job_id: str) -> None:
    JOBS[job_id]["status"] = "running"
    await asyncio.sleep(JOB_SECONDS)  # stands for the real work: a big query, a PDF, an export
    JOBS[job_id].update(status="done", result={"rows": 1250, "download": f"/reports/{job_id}/file"})


@app.post("/reports", status_code=202)
async def create_report(response: Response):
    job_id = uuid.uuid4().hex[:8]
    JOBS[job_id] = {"id": job_id, "status": "queued"}
    task = asyncio.create_task(run_job(job_id))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    # Location: where to look for the outcome. Retry-After: seconds to wait before the first look.
    response.headers["Location"] = f"/reports/{job_id}"
    response.headers["Retry-After"] = "1"
    return JOBS[job_id]


@app.get("/reports/{job_id}")
def get_report(job_id: str, response: Response):
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(404, "Report not found.")
    if job["status"] != "done":
        response.headers["Retry-After"] = "1"  # still working: ask again later
    return job
