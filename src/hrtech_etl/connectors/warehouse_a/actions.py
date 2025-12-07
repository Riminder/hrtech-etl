# src/hrtech_etl/connectors/warehouse_a/actions.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel

from hrtech_etl.core.auth import BaseAuth

from .models import WarehouseAJob, WarehouseAProfile


class WarehouseAActions(BaseModel):
    """
    Low-level client for Warehouse A (HTTP, DB, SDK, ...).

    - NO knowledge of Conditions, Cursor, or unified models.
    - Only deals with:
        * native models (WarehouseAJob / WarehouseAProfile)
        * concrete HTTP params (dict)
    """

    auth: BaseAuth

    class Config:
        arbitrary_types_allowed = True

    # Example HTTP helper (pseudo-code)
    def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Replace this with real HTTP logic (e.g. requests, httpx).
        """
        url = self.auth.build_url(path)
        headers = self.auth.build_headers()
        # resp = requests.get(url, headers=headers, params=params)
        # resp.raise_for_status()
        # return resp.json()
        raise NotImplementedError(f"Implement HTTP GET {url} with params={params!r}")
    
    def _post(self, path: str, json_body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Replace this with real HTTP logic (e.g. requests, httpx).
        """
        url = self.auth.build_url(path)
        headers = self.auth.build_headers()
        # resp = requests.post(url, headers=headers, json=json_body)
        # resp.raise_for_status()
        # return resp.json()
        raise NotImplementedError(f"Implement HTTP POST {url} with body={json_body!r}")


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
