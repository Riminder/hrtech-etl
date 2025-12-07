from __future__ import annotations

from typing import Any, Dict, List

import requests
from pydantic import BaseModel

from hrtech_etl.connectors.hrflow.models import (
    WarehouseHrflowJob,
    WarehouseHrflowProfile,
)
from hrtech_etl.core.auth import ApiKeyAuth


class WarehouseHrflowActions(BaseModel):
    """
    Low-level client for Warehouse A (HTTP, DB, SDK, ...).
    Replace the bodies with real logic.
    """

    auth: ApiKeyAuth

    class Config:
        arbitrary_types_allowed = True

    def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = self.auth.build_url(path)
        headers = self.auth.build_headers()
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        return resp

    def _post(self, path: str, json_body: Dict[str, Any]) -> Dict[str, Any]:
        url = self.auth.build_url(path)
        headers = self.auth.build_headers()
        resp = requests.post(url, headers=headers, json=json_body)
        resp.raise_for_status()
        return resp

    def _put(self, path: str, json_body: Dict[str, Any]) -> Dict[str, Any]:
        url = self.auth.build_url(path)
        headers = self.auth.build_headers()
        resp = requests.put(url, headers=headers, json=json_body)
        resp.raise_for_status()
        return resp

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

    def upsert_jobs(self, jobs: List[WarehouseHrflowJob]) -> None:
        """
        Upsert jobs in Warehouse HrFlow.ai.
        """
        for job in jobs:
            # Check if it's a creation or an update
            resp = self._get(
                "/job/indexing",
                params={
                    "board_key": job.board_key,
                    "key": job.key,
                },
            )
            if resp.status_code == 200:
                send_request = self._post
            elif resp.status_code == 400:
                send_request = self._put
            else:
                resp.raise_for_status()

            # Send the upsert request
            resp = send_request(
                "/job/indexing",
                json_body={
                    "board_key": job.board_key,
                    "job": job.dict(),
                },
            )

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

    def upsert_profiles(self, profiles: List[WarehouseHrflowProfile]) -> None:
        for profile in profiles:
            # Check if it's a creation or an update
            resp = self._get(
                "/profile/indexing",
                params={
                    "source_key": profile.source_key,
                    "key": profile.key,
                },
            )
            if resp.status_code == 200:
                send_request = self._post
            elif resp.status_code == 400:
                send_request = self._put
            else:
                resp.raise_for_status()

            # Send the upsert request
            resp = send_request(
                "/profile/indexing",
                json_body={
                    "source_key": profile.source_key,
                    "profile": profile.dict(),
                },
            )

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
