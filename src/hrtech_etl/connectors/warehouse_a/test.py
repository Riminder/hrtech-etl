# src/hrtech_etl/connectors/warehouse_a/test.py
from datetime import datetime
from typing import List, Optional, Dict, Any

from hrtech_etl.core.types import Resource, Cursor, CursorMode, PushMode
from hrtech_etl.core.pipeline import pull, push
from hrtech_etl.core.auth import BaseAuth
from .models import WarehouseAJob, WarehouseAProfile
from .requests import WarehouseARequests
from . import WarehouseAConnector


class DummyAuth(BaseAuth):
    def apply(self, headers: Dict[str, str]) -> Dict[str, str]:
        return headers


class DummyRequests(WarehouseARequests):
    def fetch_jobs(
        self,
        where: Dict[str, Any] | None,
        cursor_start: Optional[str],
        cursor_mode: str,
        limit: int,
    ) -> tuple[List[WarehouseAJob], Optional[str]]:
        job = WarehouseAJob(
            job_id="job-1",
            title="Engineer",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            payload={},
        )
        return [job], None

    def upsert_jobs(self, jobs: List[WarehouseAJob]) -> None:
        pass

    def fetch_jobs_by_ids(self, job_ids: List[str]) -> List[WarehouseAJob]:
        return []

    # implement trivial profile methods similarly...
    # ...


def test_pull_jobs_basic():
    origin = WarehouseAConnector(auth=DummyAuth(), requests=DummyRequests(base_url="", api_key="x"))
    target = WarehouseAConnector(auth=DummyAuth(), requests=DummyRequests(base_url="", api_key="y"))

    cursor = Cursor(mode=CursorMode.UPDATED_AT, start=None)
    new_cursor = pull(
        resource=Resource.JOB,
        origin=origin,
        target=target,
        cursor=cursor,
    )

    assert new_cursor.mode == CursorMode.UPDATED_AT
