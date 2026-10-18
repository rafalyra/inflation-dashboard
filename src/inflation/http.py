"""A polite, defensive HTTP client shared by every adapter.

Official APIs fail in odd ways: SGS sometimes answers HTTP 200 with an HTML error page or a
JSON error body, and its firewall blocks clients that send bursts of requests. So every
request is throttled per host, retried with backoff, and checked by a caller-supplied
validator before the body is accepted.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

import httpx

USER_AGENT = "inflation-dashboard/0.1 (+https://github.com/rafalyra/inflation-dashboard)"


class FetchError(RuntimeError):
    """A request kept failing after all retries; the message says why."""


class BadResponse(ValueError):
    """Raised by a validator when a response arrived but isn't usable data."""


Validator = Callable[[httpx.Response], None]


def require_json(response: httpx.Response) -> None:
    content_type = response.headers.get("content-type", "")
    if "json" not in content_type:
        raise BadResponse(f"expected JSON, got {content_type or 'no content type'}")


@dataclass
class PoliteClient:
    min_interval_s: float = 1.0
    retries: int = 4
    backoff_s: float = 5.0
    timeout_s: float = 60.0
    _last_request: dict[str, float] = field(default_factory=dict)
    _client: httpx.Client | None = None

    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                timeout=self.timeout_s,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
            )
        return self._client

    def _wait_turn(self, host: str) -> None:
        elapsed = time.monotonic() - self._last_request.get(host, 0.0)
        if elapsed < self.min_interval_s:
            time.sleep(self.min_interval_s - elapsed)
        self._last_request[host] = time.monotonic()

    def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        validate: Validator = require_json,
    ) -> httpx.Response:
        host = urlsplit(url).netloc
        problems: list[str] = []
        for attempt in range(self.retries + 1):
            if attempt:
                time.sleep(self.backoff_s * 3 ** (attempt - 1))
            self._wait_turn(host)
            try:
                response = self._http().get(url, params=params)
                response.raise_for_status()
                validate(response)
                return response
            except (httpx.HTTPError, BadResponse) as exc:
                problems.append(f"attempt {attempt + 1}: {exc}")
        raise FetchError(f"GET {url} failed: " + "; ".join(problems))

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
