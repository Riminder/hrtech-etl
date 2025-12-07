from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests
from pydantic import BaseModel

from hrtech_etl.connectors.hrflow.models import (
    WarehouseHrflowJob,
    WarehouseHrflowProfile,
)
<<<<<<< HEAD
=======
from hrtech_etl.core.types import Cursor, CursorMode
from hrtech_etl.core.utils import get_cursor_native_value
>>>>>>> 99ea15725f3c7536a21f400012294505b2074db3


class WarehouseHrflowActions(BaseModel):
    """
    Low-level client for Warehouse A (HTTP, DB, SDK, ...).
    Replace the bodies with real logic.
    """

    base_url: str
    api_key: str
    # FIXME: api_user_email

    # --- JOBS ---

    def fetch_jobs(
        self,
        params: Dict[str, Any],
    ) -> List[WarehouseHrflowJob]:
        """
        Translate `where` + cursor into query params and call Warehouse HrFlow.ai.
        Return (jobs, next_cursor_str_or_none).
        """

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

        return jobs

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
        params: Dict[str, Any],
    ) -> List[WarehouseHrflowProfile]:
        """
        Execute a GET /profiles (or equivalent) with the given query params.
        """

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
        return profiles

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
