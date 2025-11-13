# hrtech_etl/connectors/warehouse_a/actions.py
from typing import List, Tuple, Optional
from ...core.actions import BaseActions
from ...core.utils import single_request
from .models import WarehouseAJob, WarehouseAProfile

Cursor = Optional[str]


class WarehouseAActions(BaseActions):
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
