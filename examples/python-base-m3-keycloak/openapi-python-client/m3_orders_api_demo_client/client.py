from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import requests


@dataclass(slots=True)
class Client:
    base_url: str = "http://127.0.0.1:8001"
    token: str | None = None
    timeout: float = 30.0
    extra_headers: dict[str, str] = field(default_factory=dict)

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", **self.extra_headers}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def request(self, method: str, path: str, *, json: Any | None = None) -> Any:
        response = requests.request(
            method=method,
            url=f"{self.base_url.rstrip('/')}{path}",
            headers=self._headers(),
            json=json,
            timeout=self.timeout,
        )
        response.raise_for_status()
        if response.content:
            return response.json()
        return None

