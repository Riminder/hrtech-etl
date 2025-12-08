# src/hrtech_etl/connectors/warehouse_a/actions.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel

from hrtech_etl.core.auth import BaseAuth
from hrtech_etl.core.actions import BaseHTTPActions

from .models import WarehouseAJob, WarehouseAProfile


class WarehouseAActions(BaseHTTPActions):
    """
    Low-level client for Warehouse A (HTTP, DB, SDK, ...).
    Uses BaseHTTPActions._get/_post + build_connector_params.

    - NO knowledge of Conditions, Cursor, or unified models.
    - Only deals with:
        * native models (WarehouseAJob / WarehouseAProfile)
        * concrete HTTP params (dict)
    """

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
        # data = self._get("/jobs", params=params)
        # jobs = data.get("jobs", [])  # depends on your API
        # return [WarehouseAJob(**job) for job in data["jobs"]]
    
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
        # data = self._get("/profiles", params=params)
        # profiles = data.get("profiles", [])  # depends on your API
        # return [WarehouseAProfile(**profile) for profile in data["profiles"]]
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
