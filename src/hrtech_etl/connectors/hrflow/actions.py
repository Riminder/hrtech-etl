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
from hrtech_etl.core.utils import get_cursor_value


class WarehouseHrflowRequests(BaseModel):
    """
    Low-level client for Warehouse A (HTTP, DB, SDK, ...).
    Replace the bodies with real logic.
    """

    base_url: str
    api_key: str
    api_user_email: str
    provider_key: str

    # --- JOBS ---

    def fetch_jobs(
        self,
        where: Dict[str, Any] | None,
        cursor_start: Optional[str],
        cursor_mode: str,
        batch_size: int,
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

        # Question: the params here are for storing list,
        # it needs to be adapted for searching if 'where' integrated.
        params = {
            "board_keys": json.dumps([self.provider_key]),
            "name": None,
            "key": None,
            "reference": None,
            "location_lat": None,
            "location_lon": None,
            "location_distance": None,
            "return_job": True,
            "page": 1,
            "limit": batch_size,
            "order_by": "asc",
        }

        if cursor_mode == CursorMode.CREATED_AT:
            params["sort_by"] = "created_at"
            if cursor_start:
                params["created_at_min"] = cursor_start
        else:
            params["sort_by"] = "updated_at"
            if cursor_start:
                params["updated_at_min"] = cursor_start

        resp = requests.get(
            f"{self.base_url}/storing/jobs",
            headers={
                "X-API-KEY": self.api_key,
                "X-USER-EMAIL": self.api_user_email,
            },
            params=params,
        )
        resp.raise_for_status()
        raw_jobs = resp.json().get("data", [])

        jobs = [WarehouseHrflowJob(**job, payload=job) for job in raw_jobs]
        next_cursor = (
            get_cursor_value(jobs[-1], CursorMode(cursor_mode)) if jobs else None
        )

        return jobs, next_cursor

    def upsert_jobs(self, jobs: List[WarehouseHrflowJob]) -> None:
        """
        Upsert jobs in Warehouse HrFlow.ai.
        """
        for job in jobs:
            # Check if it's a creation or an update
            resp = requests.get(
                f"{self.base_url}/job/indexing",
                headers={
                    "X-API-KEY": self.api_key,
                    "X-USER-EMAIL": self.api_user_email,
                },
                params={
                    "board_key": self.provider_key,
                    "key": job.key,
                },
            )
            if resp.status_code == 200:
                request_method = "POST"
            elif resp.status_code == 400:
                request_method = "PUT"
            else:
                resp.raise_for_status()

            # Send the upsert request
            resp = requests(
                request_method,
                f"{self.base_url}/job/indexing",
                headers={
                    "X-API-KEY": self.api_key,
                    "X-USER-EMAIL": self.api_user_email,
                },
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
        jobs = []
        for key in job_ids:
            resp = requests.get(
                f"{self.base_url}/job/indexing",
                headers={
                    "X-API-KEY": self.api_key,
                    "X-USER-EMAIL": self.api_user_email,
                },
                params={
                    "board_key": self.provider_key,
                    "key": key,
                },
            )
            # Question: what if not found?
            if resp.status_code == 200:
                jobs.append(
                    WarehouseHrflowJob(**resp.json().get("data"), payload=resp.json())
                )
            else:
                resp.raise_for_status()
        return jobs

    # --- PROFILES ---

    def fetch_profiles(
        self,
        where: Dict[str, Any] | None,
        cursor_start: Optional[str],
        cursor_mode: str,
        batch_size: int,
    ) -> tuple[List[WarehouseHrflowProfile], Optional[str]]:
        if cursor_mode not in [
            CursorMode.CREATED_AT.value,
            CursorMode.UPDATED_AT.value,
        ]:
            raise ValueError(f"Unsupported cursor mode: {cursor_mode}")

        # Question: the params here are for storing list,
        # it needs to be adapted for searching if 'where' integrated.
        params = {
            "source_keys": json.dumps([self.provider_key]),
            "name": None,
            "key": None,
            "email": None,
            "reference": None,
            "location_lat": None,
            "location_lon": None,
            "location_distance": None,
            "return_profile": True,
            "page": 1,
            "limit": batch_size,
            "order_by": "asc",
        }

        if cursor_mode == CursorMode.CREATED_AT:
            params["sort_by"] = "created_at"
            if cursor_start:
                params["created_at_min"] = cursor_start
        else:
            params["sort_by"] = "updated_at"
            if cursor_start:
                params["updated_at_min"] = cursor_start

        resp = requests.get(
            f"{self.base_url}/storing/profiles",
            headers={
                "X-API-KEY": self.api_key,
                "X-USER-EMAIL": self.api_user_email,
            },
            params=params,
        )
        resp.raise_for_status()
        raw_profiles = resp.json().get("data", [])

        profiles = [
            WarehouseHrflowProfile(**profile, payload=profile)
            for profile in raw_profiles
        ]
        next_cursor = (
            get_cursor_value(profiles[-1], CursorMode(cursor_mode))
            if profiles
            else None
        )

        return profiles, next_cursor

    def upsert_profiles(self, profiles: List[WarehouseHrflowProfile]) -> None:
        for profile in profiles:
            # Check if it's a creation or an update
            resp = requests.get(
                f"{self.base_url}/profile/indexing",
                headers={
                    "X-API-KEY": self.api_key,
                    "X-USER-EMAIL": self.api_user_email,
                },
                params={
                    "source_key": self.provider_key,
                    "key": profile.key,
                },
            )
            if resp.status_code == 200:
                request_method = "POST"
            elif resp.status_code == 400:
                request_method = "PUT"
            else:
                resp.raise_for_status()

            # Send the upsert request
            resp = requests(
                request_method,
                f"{self.base_url}/profile/indexing",
                headers={
                    "X-API-KEY": self.api_key,
                    "X-USER-EMAIL": self.api_user_email,
                },
                json={
                    "source_key": self.provider_key,
                    "profile": profile.dict(),
                },
            )
            resp.raise_for_status()

    def fetch_profiles_by_ids(
        self, profile_ids: List[str]
    ) -> List[WarehouseHrflowProfile]:
        profiles = []
        for key in profile_ids:
            resp = requests.get(
                f"{self.base_url}/profile/indexing",
                headers={
                    "X-API-KEY": self.api_key,
                    "X-USER-EMAIL": self.api_user_email,
                },
                params={
                    "source_key": self.provider_key,
                    "key": key,
                },
            )
            # Question: what if not found?
            if resp.status_code == 200:
                profiles.append(
                    WarehouseHrflowProfile(
                        **resp.json().get("data"), payload=resp.json()
                    )
                )
            else:
                resp.raise_for_status()
        return profiles
