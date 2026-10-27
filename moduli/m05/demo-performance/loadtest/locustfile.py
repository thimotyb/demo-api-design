"""Load test of GET /products/1: a client that always downloads against one that revalidates.

Both kinds of user send the same number of requests. The conditional user remembers the ETag
and sends it back in If-None-Match, so the server answers 304 with no body after the first
request. Compare the response sizes and the latency percentiles in the summary.
"""

from locust import HttpUser, constant, task


class PlainReader(HttpUser):
    wait_time = constant(0.05)

    @task
    def read(self):
        self.client.get("/products/1", name="plain GET")


class ConditionalReader(HttpUser):
    wait_time = constant(0.05)

    def on_start(self):
        self.etag = None

    @task
    def read(self):
        headers = {"If-None-Match": self.etag} if self.etag else {}
        with self.client.get("/products/1", headers=headers, name="conditional GET", catch_response=True) as response:
            if response.status_code in (200, 304):
                self.etag = response.headers.get("ETag", self.etag)
                response.success()
            else:
                response.failure(f"unexpected status {response.status_code}")
