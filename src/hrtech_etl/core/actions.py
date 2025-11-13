# hrtech_etl/core/actions.py
from typing import Any


class BaseActions:
    def __init__(self, client: Any):
        """
        client: HTTP client, DB client, SDK, etc.
        """
        self._client = client
        self._request_count = 0

    def _request(self, *args, **kwargs):
        """
        Single low-level request entrypoint.
        Concrete actions must call ONLY this for I/O.
        """
        self._request_count += 1
        return self._client.request(*args, **kwargs)
