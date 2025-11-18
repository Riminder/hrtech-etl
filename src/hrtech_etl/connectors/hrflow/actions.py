from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import requests
from pydantic import BaseModel

from hrtech_etl.connectors.hrflow.models import (
    WarehouseHrflowJob,
    WarehouseHrflowProfile,
)
from hrtech_etl.core.types import CursorMode


class WarehouseHrflowRequests(BaseModel):
    """
    Low-level client for Warehouse A (HTTP, DB, SDK, ...).
    Replace the bodies with real logic.
    """

    base_url: str
    api_key: str
    provider_key: str

    # --- JOBS ---

    def fetch_jobs(
        self,
        where: Dict[str, Any] | None,
        cursor_start: Optional[str],
        cursor_mode: str,
        limit: int,
    ) -> tuple[List[WarehouseHrflowJob], Optional[str]]:
        """
        Translate `where` + cursor into query params and call Warehouse HrFlow.ai.
        Return (jobs, next_cursor_str_or_none).
        """

        if cursor_mode not in [
            CursorMode.CREATED_AT.value,
            CursorMode.UPDATED_AT.value,
        ]:
            raise ValueError(f"Unsupported cursor mode: {cursor_mode}")

        # FIXME: lister tous les paramètres possibles
        params: Dict[str, Any] = {
            "board_keys": json.dumps([self.provider_key]),
            "page": 1,
            "limit": limit,
            "return_job": "true",
            "order_by": "asc",
        }

        if cursor_mode == CursorMode.CREATED_AT:
            params["sort_by"] = "created_at"
        else:
            params["sort_by"] = "updated_at"

        resp = requests.get(
            f"{self.base_url}/storing/jobs",
            headers={"X-API-Key": self.api_key},
            params=params,
        )
        resp.raise_for_status()
        raw_jobs = resp.json().get("data", [])

        # FIXME: payload not handled, add all mapping in warehouse
        jobs = [WarehouseHrflowJob(**job).dict() for job in raw_jobs]

        if cursor_mode == CursorMode.CREATED_AT.value:
            next_cursor = jobs[-1].get("created_at")
        elif cursor_mode == CursorMode.UPDATED_AT.value:
            next_cursor = jobs[-1].get("updated_at")
        else:
            next_cursor = None

        return jobs, next_cursor

    def upsert_jobs(self, jobs: List[WarehouseHrflowJob]) -> None:
        """
        Upsert jobs in Warehouse HrFlow.ai.
        """
        for job in jobs:
            # FIXME: distinguer create (post) et update (put)
            job["reference"] = job["key"]
            resp = requests.post(
                f"{self.base_url}/job/indexing",
                headers={"X-API-Key": self.api_key},
                json={
                    "board_key": self.provider_key,
                    "job": job.dict(),
                },
            )
            resp.raise_for_status()

    def fetch_jobs_by_ids(self, job_ids: List[str]) -> List[WarehouseHrflowJob]:
        """
        For event-based push: fetch jobs by IDs.
        """
        raise NotImplementedError

    # --- PROFILES ---

    def fetch_profiles(
        self,
        where: Dict[str, Any] | None,
        cursor_start: Optional[str],
        cursor_mode: str,
        limit: int,
    ) -> tuple[List[WarehouseHrflowProfile], Optional[str]]:
        raise NotImplementedError

    def upsert_profiles(self, profiles: List[WarehouseHrflowProfile]) -> None:
        raise NotImplementedError

    def fetch_profiles_by_ids(
        self, profile_ids: List[str]
    ) -> List[WarehouseHrflowProfile]:
        raise NotImplementedError
