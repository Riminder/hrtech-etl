# hrtech_etl/core/auth.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any


class BaseAuth(ABC):
    def __init__(self, base_url: str, extra_headers: Optional[Dict[str, str]] = None):
        self.base_url = base_url.rstrip("/")
        self._extra_headers = extra_headers or {}

    @abstractmethod
    def as_headers(self) -> Dict[str, str]:
        """
        Return the *auth-specific* HTTP headers (e.g. Authorization, X-API-Key, ...).
        """
        ...

    def build_headers(self, more: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Merge:
          - auth headers
          - static extra headers (passed at init)
          - per-request headers (more)
        """
        headers = dict(self.as_headers())
        headers.update(self._extra_headers)
        if more:
            headers.update(more)
        return headers

    def build_url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"


class ApiKeyAuth(BaseAuth):
    def __init__(
        self,
        base_url: str,
        header_name: str,
        api_key: str,
        extra_headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(base_url=base_url, extra_headers=extra_headers)
        self.header_name = header_name
        self.api_key = api_key

    def as_headers(self) -> Dict[str, str]:
        return {self.header_name: self.api_key}


class TokenAuth(BaseAuth):
    def __init__(
        self,
        base_url: str,
        token: str,
        scheme: str = "Token",
        extra_headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(base_url=base_url, extra_headers=extra_headers)
        self.token = token
        self.scheme = scheme

    def as_headers(self) -> Dict[str, str]:
        return {"Authorization": f"{self.scheme} {self.token}"}


class BearerAuth(BaseAuth):
    def __init__(
        self,
        base_url: str,
        token: str,
        extra_headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(base_url=base_url, extra_headers=extra_headers)
        self.token = token

    def as_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

_AUTH_KINDS = {
    "api_key": ApiKeyAuth,
    "bearer": BearerAuth,
    "token": TokenAuth,
}


def build_auth_from_payload(
    auth_payload: dict[str, Any],
    default_auth: BaseAuth,
) -> BaseAuth:
    """
    Build a concrete auth object from JSON payload.

    If 'auth_type' is present, we use it to select the subclass.
    Otherwise we fall back to the default_auth's class.
    """
    if not auth_payload:
        return default_auth

    auth_type = auth_payload.get("auth_type") or auth_payload.get("type")
    if auth_type:
        auth_cls = _AUTH_KINDS.get(auth_type)
        if auth_cls is None:
            raise ValueError(f"Unknown auth_type: {auth_type!r}")
    else:
        auth_cls = type(default_auth)

    # Pydantic v2
    return auth_cls.model_validate(auth_payload)

"""
auth = ApiKeyAuth(
    base_url="https://api.warehouse-a.example",
    header_name="X-API-Key",
    api_key="secret",
    extra_headers={
        "X-Tenant-ID": "tenant-123",
        "X-Correlation-ID": "my-corr-id",
    },
)

headers = auth.build_headers()
# or per-request:
headers = auth.build_headers({"X-Request-ID": "req-42"})

# Then in WarehouseAActions:

resp = requests.get(
    auth.build_url("/jobs"),
    headers=auth.build_headers(),   # or build_headers({...})
    params=params,
)

# Or with signature:
headers = auth.build_headers({
    "X-Signature": compute_signature(params),
})



"""