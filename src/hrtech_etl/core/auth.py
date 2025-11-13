from abc import ABC, abstractmethod
from typing import Dict


class BaseAuth(ABC):
    @abstractmethod
    def as_headers(self) -> Dict[str, str]:
        """
        Return HTTP headers or equivalent auth representation.
        """
        ...


class ApiKeyAuth(BaseAuth):
    def __init__(self, header_name: str, api_key: str):
        self.header_name = header_name
        self.api_key = api_key

    def as_headers(self) -> Dict[str, str]:
        return {self.header_name: self.api_key}


class TokenAuth(BaseAuth):
    def __init__(self, token: str, scheme: str = "Token"):
        self.token = token
        self.scheme = scheme

    def as_headers(self) -> Dict[str, str]:
        return {"Authorization": f"{self.scheme} {self.token}"}


class BearerAuth(BaseAuth):
    def __init__(self, token: str):
        self.token = token

    def as_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}
