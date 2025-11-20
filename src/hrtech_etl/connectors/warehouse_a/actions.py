# src/hrtech_etl/connectors/warehouse_a/actions.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from .models import WarehouseAJob, WarehouseAProfile
from hrtech_etl.core.types import Cursor, CursorMode, Condition


class WarehouseAActions(BaseModel):
    """
    Low-level client for Warehouse A (HTTP, DB, SDK, ...).
    Replace the bodies with real logic.
    """

    base_url: str
    api_key: str

    # --- JOBS ---

    def fetch_jobs(
        self,
        cursor: Cursor=Cursor(mode=CursorMode.UPDATED_AT, start=None, sort_by="asc"),
        where: Dict[str, Any] | None = None,
        batch_size: int= 1000,
    ) -> tuple[List[WarehouseAJob], Optional[str]]:
        """
        Translate `where` + cursor into query params and call Warehouse A.
        Return (jobs, next_cursor_str_or_none).
        """
        raise NotImplementedError

    def upsert_jobs(self, jobs: List[WarehouseAJob]) -> None:
        """
        Upsert jobs in Warehouse A.
        """
        raise NotImplementedError

    def fetch_jobs_by_ids(self, job_ids: List[str]) -> List[WarehouseAJob]:
        """
        For event-based push: fetch jobs by IDs.
        """
        raise NotImplementedError

    # --- PROFILES ---

    def fetch_profiles(
        self,
        where: list[Condition] | None,
        cursor: Cursor=Cursor(mode=CursorMode.UPDATED_AT, start=None, sort_by="asc"),
        batch_size: int= 1000,
    ) -> tuple[List[WarehouseAProfile], Optional[str]]:
        raise NotImplementedError

    def upsert_profiles(self, profiles: List[WarehouseAProfile]) -> None:
        raise NotImplementedError

    def fetch_profiles_by_ids(self, profile_ids: List[str]) -> List[WarehouseAProfile]:
        raise NotImplementedError
