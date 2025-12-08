from __future__ import annotations

from typing import Any, Dict, List

from hrtech_etl.connectors.hrflow.models import (
    WarehouseHrflowJob,
    WarehouseHrflowProfile,
)
from hrtech_etl.core.actions import BaseHTTPActions


class WarehouseHrflowActions(BaseHTTPActions):
    """
    Low-level client for Warehouse A (HTTP, DB, SDK, ...).
    Replace the bodies with real logic.
    """

    # ------------------------------------------------------------------
    # JOBS
    # ------------------------------------------------------------------

    def fetch_jobs(
        self,
        params: Dict[str, Any],
    ) -> List[WarehouseHrflowJob]:
        """
        Translate `where` + cursor into query params and call Warehouse HrFlow.ai.
        Return (jobs, next_cursor_str_or_none).
        """

        resp = self._get("/storing/jobs", params=params)
        raw_jobs = resp.json().get("data", [])
        jobs = [WarehouseHrflowJob(**job, payload=job) for job in raw_jobs]

        return jobs

    def create_jobs(self, jobs: List[WarehouseHrflowJob]) -> List[Dict[str, Any]]:
        """
        Upsert jobs in Warehouse HrFlow.ai.
        """
        response = []
        for job in jobs:
            resp = self._post(
                "/job/indexing",
                json_body={
                    "board_key": job.board_key,
                    "job": job.dict(),
                },
            )
            response.append(resp)
        return response

    def update_jobs(self, jobs: List[WarehouseHrflowJob]) -> List[Dict[str, Any]]:
        """
        Update jobs in Warehouse HrFlow.ai.
        """
        response = []
        for job in jobs:
            resp = self._put(
                "/job/indexing",
                json_body={
                    "board_key": job.board_key,
                    "job": job.dict(),
                },
            )
            response.append(resp)
        return response

    def fetch_jobs_by_ids(self, job_ids: List[str]) -> List[WarehouseHrflowJob]:
        """
        For event-based push: fetch jobs by IDs.
        """
        jobs = []
        for key in job_ids:
            resp = self._get(
                "/job/indexing",
                params={
                    "board_key": self.provider_key,
                    "key": key,
                },
            )
            if resp.status_code == 200:
                jobs.append(
                    WarehouseHrflowJob(**resp.json().get("data"), payload=resp.json())
                )
        return jobs

    # ------------------------------------------------------------------
    # PROFILES
    # ------------------------------------------------------------------

    def fetch_profiles(
        self,
        params: Dict[str, Any],
    ) -> List[WarehouseHrflowProfile]:
        """
        Execute a GET /profiles (or equivalent) with the given query params.
        """

        resp = self._get("/storing/profiles", params=params)
        raw_profiles = resp.json().get("data", [])
        profiles = [
            WarehouseHrflowProfile(**profile, payload=profile)
            for profile in raw_profiles
        ]

        return profiles

    def create_profiles(
        self, profiles: List[WarehouseHrflowProfile]
    ) -> List[Dict[str, Any]]:
        response = []
        for profile in profiles:
            resp = self._post(
                "/profile/indexing",
                json_body={
                    "source_key": profile.source_key,
                    "profile": profile.dict(),
                },
            )
            response.append(resp)
        return response

    def update_profiles(
        self, profiles: List[WarehouseHrflowProfile]
    ) -> List[Dict[str, Any]]:
        response = []
        for profile in profiles:
            resp = self._put(
                "/profile/indexing",
                json_body={
                    "source_key": profile.source_key,
                    "profile": profile.dict(),
                },
            )
            response.append(resp)
        return response

    def fetch_profiles_by_ids(
        self, profile_ids: List[str]
    ) -> List[WarehouseHrflowProfile]:
        profiles = []
        for key in profile_ids:
            resp = self._get(
                "/profile/indexing",
                params={
                    "source_key": self.provider_key,
                    "key": key,
                },
            )

            if resp.status_code == 200:
                profiles.append(
                    WarehouseHrflowProfile(
                        **resp.json().get("data"), payload=resp.json()
                    )
                )
        return profiles
