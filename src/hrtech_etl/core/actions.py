# hrtech_etl/core/actions.py
from __future__ import annotations

from typing import Any, Dict, Optional, Protocol

from pydantic import BaseModel
import requests


from .auth import BaseAuth

class RequestClient(Protocol):
    """
    Protocol for clients that provide a 'request' method.
    This ensures type checking for the client passed to BaseActions.
    """

    def request(self, *args: Any, **kwargs: Any) -> Any: ...


class BaseActions:
    def __init__(self, client: RequestClient):
        """
        Initializes the BaseActions with a client.
        Base class for connector-specific request layers.

        The client is expected to provide a 'request' method for I/O operations.
        Examples include HTTP clients, DB clients, or SDKs.

        Args:
            client: An object conforming to the RequestClient protocol,
                    providing a 'request' method.

        It typically wraps an HTTP client or DB client and exposes:
        - fetch_jobs(...)
        - fetch_profiles(...)
        - upsert_jobs(...)
        - upsert_profiles(...)
        while keeping track of low-level request counts, retries, etc.
        """
        self._client = client
        self._request_count = 0

    @property
    def request_count(self) -> int:
        """
        Returns the number of requests made through this action instance.
        """
        return self._request_count

    def _request(self, *args: Any, **kwargs: Any) -> Any:
        """
        Single low-level request entrypoint for I/O operations.

        This method increments an internal request counter and delegates the
        actual request execution to the underlying client's 'request' method.
        Concrete action methods in subclasses should call ONLY this method for I/O.

        Args:
            *args: Positional arguments to pass to the client's request method.
            **kwargs: Keyword arguments to pass to the client's request method.

        Returns:
            The result of the client's request method.
        """
        self._request_count += 1
        return self._client.request(*args, **kwargs)


class BaseHTTPActions(BaseModel):
    """
    Base class for HTTP-based actions.

    - Holds a BaseAuth
    - Provides convenience _get / _post methods
    - You override or extend per connector if needed
    """

    auth: BaseAuth

    class Config:
        arbitrary_types_allowed = True

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Replace this with real HTTP logic (e.g. requests, httpx).
        """
        url = self.auth.build_url(path)
        headers = self.auth.build_headers()
        return requests.get(url, headers=headers, params=params or {})

    def _post(self, path: str, json_body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Replace this with real HTTP logic (e.g. requests, httpx).
        """
        url = self.auth.build_url(path)
        headers = self.auth.build_headers()
        return requests.post(url, headers=headers, json=json_body)
 
    def _put(self, path: str, json_body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Replace this with real HTTP logic (e.g. requests, httpx).
        """
        url = self.auth.build_url(path)
        headers = self.auth.build_headers()
        return requests.put(url, headers=headers, json=json_body)

