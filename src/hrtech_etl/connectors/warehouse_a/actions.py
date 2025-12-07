# src/hrtech_etl/connectors/warehouse_a/actions.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel

from .models import WarehouseAJob, WarehouseAProfile


class WarehouseAActions(BaseModel):
    """
    Low-level client for Warehouse A (HTTP, DB, SDK, ...).

    - NO knowledge of Conditions, Cursor, or unified models.
    - Only deals with:
        * native models (WarehouseAJob / WarehouseAProfile)
        * concrete HTTP params (dict)
    """

    base_url: str
    api_key: str
    headers: Dict[str, str]

    # ------------------------------------------------------------------
    # JOBS
    # ------------------------------------------------------------------

    def fetch_jobs(
        self,
        params: Dict[str, Any],
    ) -> List[WarehouseAJob]:
        """
        Execute a GET /jobs (or equivalent) with the given query params.

        Returns:
          (list_of_jobs, next_cursor_str_or_none)
        """
        # ---- TODO: replace with real HTTP call ----
        #
        # import requests
        # headers = {"Authorization": f"Bearer {self.api_key}"}
        # resp = requests.get(f"{self.base_url}/jobs", headers=headers, params=params)
        # resp.raise_for_status()
        # data = resp.json()
        # jobs = [WarehouseAJob(**item) for item in data["items"]]
        # next_cursor = data.get("next_cursor")
        # return jobs
        #
        raise NotImplementedError(f"Implement HTTP GET /jobs with params={params!r}")

    def upsert_jobs(self, jobs: List[WarehouseAJob]) -> None:
        """
        Upsert jobs in Warehouse A.
        """
        # ---- TODO: implement POST/PUT /jobs ----
        raise NotImplementedError

    def fetch_jobs_by_ids(self, job_ids: List[str]) -> List[WarehouseAJob]:
        """
        For event-based push: fetch jobs by IDs.
        """
        # ---- TODO: implement GET /jobs?ids=... or similar ----
        raise NotImplementedError

    # ------------------------------------------------------------------
    # PROFILES
    # ------------------------------------------------------------------

    def fetch_profiles(
        self,
        params: Dict[str, Any],
    ) -> List[WarehouseAProfile]:
        """
        Execute a GET /profiles (or equivalent) with the given query params.
        """
        # ---- TODO: replace with real HTTP call ----
        #
        # import requests
        # headers = {"Authorization": f"Bearer {self.api_key}"}
        # resp = requests.get(f"{self.base_url}/profiles", headers=headers, params=params)
        # resp.raise_for_status()
        # data = resp.json()
        # profiles = [WarehouseAProfile(**item) for item in data["items"]]
        # next_cursor = data.get("next_cursor")
        # return profiles
        #
        raise NotImplementedError(f"Implement HTTP GET /profiles with params={params!r}")

    def upsert_profiles(self, profiles: List[WarehouseAProfile]) -> None:
        """
        Upsert profiles in Warehouse A.
        """
        # ---- TODO: implement POST/PUT /profiles ----
        raise NotImplementedError

    def fetch_profiles_by_ids(self, profile_ids: List[str]) -> List[WarehouseAProfile]:
        """
        For event-based push: fetch profiles by IDs.
        """
        # ---- TODO: implement GET /profiles?ids=... or similar ----
        raise NotImplementedError
