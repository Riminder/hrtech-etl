# src/hrtech_etl/connectors/warehouse_a/test.py
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi.testclient import TestClient
from pydantic import BaseModel

from hrtech_etl.core.auth import BaseAuth
from hrtech_etl.core.pipeline import pull, push
from hrtech_etl.core.registry import ConnectorMeta, register_connector
from hrtech_etl.core.types import (
    Condition,
    Cursor,
    CursorMode,
    PushMode,
    Resource,
    WarehouseType,
)
from hrtech_etl.connectors.warehouse_a import WarehouseAConnector
from hrtech_etl.connectors.warehouse_a.actions import WarehouseAActions
from hrtech_etl.connectors.warehouse_a.models import WarehouseAJob, WarehouseAProfile

from app.main import create_app


# ---------------------------------------------------------------------------
# Dummy implementations (shared between direct connector tests & API tests)
# ---------------------------------------------------------------------------


class DummyAuth(BaseAuth):
    """Auth that does nothing (used for tests)."""

    def apply(self, headers: Dict[str, str]) -> Dict[str, str]:
        return headers


class DummyActions(WarehouseAActions):
    """
    Dummy WarehouseAActions for tests.

    - fetch_* returns in-memory data (no HTTP)
    - upsert_* are no-ops
    """

    def fetch_jobs(
        self,
        cursor: Cursor = Cursor(mode=CursorMode.UPDATED_AT, start=None, sort_by="asc"),
        where: List[Condition] | None = None,
        batch_size: int = 1000,
    ) -> tuple[List[WarehouseAJob], Optional[str]]:
        now = datetime.utcnow()
        job = WarehouseAJob(
            job_id="job-1",
            title="Engineer",
            created_at=now,
            updated_at=now,
            payload={},
        )
        # No pagination in this dummy: we always return a single batch, no next_cursor
        return [job], None

    def upsert_jobs(self, jobs: List[WarehouseAJob]) -> None:
        # No-op in tests
        return None

    def fetch_jobs_by_ids(self, job_ids: List[str]) -> List[WarehouseAJob]:
        # For push(EVENTS) tests you can implement something similar here if needed
        return []

    def fetch_profiles(
        self,
        cursor: Cursor = Cursor(mode=CursorMode.UPDATED_AT, start=None, sort_by="asc"),
        where: List[Condition] | None = None,
        batch_size: int = 1000,
    ) -> tuple[List[WarehouseAProfile], Optional[str]]:
        now = datetime.utcnow()
        profile = WarehouseAProfile(
            profile_id="profile-1",
            full_name="John Doe",
            created_at=now,
            updated_at=now,
            payload={},
        )
        return [profile], None

    def upsert_profiles(self, profiles: List[WarehouseAProfile]) -> None:
        # No-op in tests
        return None

    def fetch_profiles_by_ids(self, profile_ids: List[str]) -> List[WarehouseAProfile]:
        return []


def _build_test_connector() -> WarehouseAConnector:
    """
    Factory used only in tests.

    Returns a WarehouseAConnector wired with DummyAuth + DummyActions
    so that FastAPI endpoints can run without external dependencies.
    """
    auth = DummyAuth()
    actions = DummyActions(base_url="https://dummy", api_key="dummy")
    return WarehouseAConnector(auth=auth, actions=actions)


# Register a dedicated test connector name to avoid clashing with the default one.
register_connector(
    ConnectorMeta(
        name="warehouse_a_test",
        label="Warehouse A (test)",
        warehouse_type=WarehouseType.JOBBOARD,
        job_model="hrtech_etl.connectors.warehouse_a.models.WarehouseAJob",
        profile_model="hrtech_etl.connectors.warehouse_a.models.WarehouseAProfile",
        connector_path="hrtech_etl.connectors.warehouse_a.WarehouseAConnector",
    ),
    factory=_build_test_connector,
)

# Build FastAPI test client (once for all tests in this module)
app = create_app()
client = TestClient(app)


# ---------------------------------------------------------------------------
# Direct connector + pipeline tests (no FastAPI)
# ---------------------------------------------------------------------------


def test_pull_jobs_basic():
    """
    Basic end-to-end pull using WarehouseAConnector + DummyActions,
    without going through the FastAPI layer.
    """
    origin = WarehouseAConnector(
        auth=DummyAuth(),
        actions=DummyActions(base_url="", api_key="x"),
    )
    target = WarehouseAConnector(
        auth=DummyAuth(),
        actions=DummyActions(base_url="", api_key="y"),
    )

    cursor = Cursor(mode=CursorMode.UPDATED_AT, start=None, sort_by="asc")

    new_cursor = pull(
        resource=Resource.JOB,
        origin=origin,
        target=target,
        cursor=cursor,
    )

    assert new_cursor.mode == CursorMode.UPDATED_AT
    # DummyActions returns a single job whose updated_at is used as end
    assert new_cursor.end is not None


# ---------------------------------------------------------------------------
# FastAPI API tests (integration through /api/ endpoints)
# ---------------------------------------------------------------------------


def test_api_connectors_lists_warehouse_a_test():
    """The /api/connectors endpoint should list our test connector."""
    resp = client.get("/api/connectors")
    assert resp.status_code == 200

    connectors = resp.json()
    names = {c["name"] for c in connectors}
    assert "warehouse_a_test" in names


def test_api_run_pull_jobs_with_test_connector():
    """
    /api/run/pull should be able to execute a pull using warehouse_a_test
    and return a valid Cursor payload.
    """
    payload: Dict[str, Any] = {
        "resource": "job",
        "origin": "warehouse_a_test",
        "target": "warehouse_a_test",
        "cursor": {
            "mode": "updated_at",
            "start": None,
            "end": None,
            "sort_by": "asc",
        },
        "where": [],           # no prefilters
        "having": [],          # no postfilters
        "formatter": None,     # use unified path
        "formatter_id": None,  # not used here but present in schema
        "batch_size": 10,
        "dry_run": False,
    }

    resp = client.post("/api/run/pull", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    # cursor schema: {mode, start, end, sort_by}
    assert data["mode"] == "updated_at"
    # since DummyActions returns one job with updated_at set, end must not be None
    assert data["end"] is not None


def test_api_run_push_resources_jobs_with_test_connector():
    """
    /api/run/push in RESOURCES mode using warehouse_a_test.
    """
    now = datetime.utcnow().isoformat()

    # minimal native WarehouseAJob payload matching the model
    resources: List[Dict[str, Any]] = [
        {
            "job_id": "job-1",
            "title": "Engineer",
            "created_at": now,
            "updated_at": now,
            "payload": {},
        }
    ]

    payload: Dict[str, Any] = {
        "resource": "job",
        "origin": "warehouse_a_test",
        "target": "warehouse_a_test",
        "mode": PushMode.RESOURCES.value,  # "resources"
        "events": None,
        "resources": resources,
        "having": [],
        "formatter": None,
        "batch_size": 100,
        "dry_run": False,
    }

    resp = client.post("/api/run/push", json=payload)
    assert resp.status_code == 200

    result = resp.json()
    assert result["total_resources_fetched"] == 1
    assert result["total_resources_pushed"] == 1
    assert result["skipped_missing"] == 0
    assert result["skipped_having"] == 0
