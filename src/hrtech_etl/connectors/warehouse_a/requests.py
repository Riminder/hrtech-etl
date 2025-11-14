# hrtech_etl/connectors/warehouse_a/actions.py
from typing import List, Tuple, Optional
from ...core.requests import BaseRequests
from ...core.utils import single_request
from .models import WarehouseAJob, WarehouseAProfile

Cursor = Optional[str]


class WarehouseARequests(BaseRequests):


    @single_request
    def fetch_jobs(
        self,
        cursor: Cursor,
        limit: int,
    ) -> Tuple[List[WarehouseAJob], Cursor]:
        resp = self._request(
            "GET",
            "/jobs",
            params={"cursor": cursor, "limit": limit},
        )
        ...
        return jobs, next_cursor

    @single_request
    def fetch_profiles(
        self,
        cursor: Cursor,
        limit: int,
    ) -> Tuple[List[WarehouseAProfile], Cursor]:
        resp = self._request(
            "GET",
            "/profiles",
            params={"cursor": cursor, "limit": limit},
        )
        ...
        return profiles, next_cursor

    @single_request
    def upsert_jobs(self, jobs: List[WarehouseAJob]) -> None:
        payload = [j.__dict__ for j in jobs]
        self._request("POST", "/jobs/bulk_upsert", json=payload)

    @single_request
    def upsert_profiles(self, profiles: List[WarehouseAProfile]) -> None:
        payload = [p.__dict__ for p in profiles]
        self._request("POST", "/profiles/bulk_upsert", json=payload)

# src/hrtech_etl/connectors/warehouse_a/requests.py
from typing import List, Tuple, Optional
from hrtech_etl.core.requests import BaseRequests
from .models import WarehouseAJob, WarehouseAProfile

Cursor = Optional[str]


class WarehouseARequests(BaseRequests):
    def __init__(self, client):
        self.client = client

    def fetch_jobs(
        self,
        cursor: Cursor,
        limit: int,
        filters: dict | None = None,
    ) -> Tuple[List[WarehouseAJob], Cursor]:
        self._record_request()
        # TODO: implement real HTTP/DB calls using self.client
        raise NotImplementedError

    def fetch_profiles(
        self,
        cursor: Cursor,
        limit: int,
        filters: dict | None = None,
    ) -> Tuple[List[WarehouseAProfile], Cursor]:
        self._record_request()
        raise NotImplementedError

    def upsert_jobs(self, jobs: List[WarehouseAJob]) -> None:
        self._record_request()
        raise NotImplementedError

    def upsert_profiles(self, profiles: List[WarehouseAProfile]) -> None:
        self._record_request()
        raise NotImplementedError
