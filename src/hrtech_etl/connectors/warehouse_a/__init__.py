# hrtech_etl/connectors/warehouse_a/__init__.py
from typing import List, Tuple, Optional, Any, Iterable
from datetime import datetime

from ...core.connector import BaseConnector, Cursor
from ...core.auth import BaseAuth
from ...core.types import WarehouseType, CursorMode, JobEventType
from ...core.models import UnifiedJob, UnifiedProfile, UnifiedJobEvent
from .models import WarehouseAJob, WarehouseAProfile, JobEvent
from .requests import WarehouseARequests

from hrtech_etl.core.registry import register_connector, ConnectorMeta


from hrtech_etl.core.registry import register_connector, ConnectorMeta
from hrtech_etl.core.types import WarehouseType, UnifiedJobEvent, Cursor, CursorMode

from hrtech_etl.core.auth import ApiKeyAuth



# Register for UI / config usage
register_connector(
    ConnectorMeta(
        name="warehouse_a",
        label="Warehouse A",
        warehouse_type=WarehouseType.JOBBOARD,
        job_model="hrtech_etl.connectors.warehouse_a.models.WarehouseAJob",
        profile_model="hrtech_etl.connectors.warehouse_a.models.WarehouseAProfile",
    )
)


class WarehouseAConnector(BaseConnector):
    job_native_cls = WarehouseAJob
    profile_native_cls = WarehouseAProfile

    def __init__(self, auth: BaseAuth, requests: WarehouseARequests):
        super().__init__(
            auth=auth,
            name="warehouse_a",
            warehouse_type=WarehouseType.JOBBOARD,
        )
        self.requests = requests

    def read_jobs_batch(
        self,
        cursor: Cursor = None,
        cursor_mode: CursorMode = CursorMode.UPDATED_AT,
        batch_size: int = 1000,
    ) -> Tuple[List[WarehouseAJob], Cursor]:
        # interpret cursor depending on mode
        if cursor_mode == CursorMode.UPDATED_AT:
            updated_after: Optional[datetime] = cursor
            jobs = self.actions.fetch_jobs(updated_after=updated_after, batch_size=batch_size)
        elif cursor_mode == CursorMode.CREATED_AT:
            created_after: Optional[datetime] = cursor
            jobs = self.actions.fetch_jobs(created_after=created_after, batch_size=batch_size)
        elif cursor_mode == CursorMode.ID:
            id_after: Optional[str] = cursor
            jobs = self.actions.fetch_jobs(id_after=id_after, batch_size=batch_size)
        else:
            raise ValueError(f"Unsupported cursor mode: {cursor_mode}")

        # here we don't need to compute next_cursor: the pipeline uses
        # get_cursor_value on the last native object as the "position"
        next_cursor = cursor  # or vendor-specific token if needed
        return jobs, next_cursor

    def _write_jobs_native(self, jobs: List[WarehouseAJob]) -> None:
        self.actions.upsert_jobs(jobs)

    def to_unified_job(self, native: WarehouseAJob) -> UnifiedJob:
        return UnifiedJob(
            id=native.job_id,
            title=native.job_title,
            location=None,  # or derive from payload
            source=self.name,
            created_at=native.created_on,
            updated_at=native.last_modified,
            raw=native.payload,
        )

    def from_unified_job(self, unified: UnifiedJob) -> WarehouseAJob:
        return WarehouseAJob(
            job_id=unified.id,
            job_title=unified.title,
            last_modified=unified.updated_at or unified.created_at or datetime.utcnow(),
            created_on=unified.created_at or datetime.utcnow(),
            payload=unified.raw or {},
        )
    
    # --- JOB EVENTS ---
    def parse_job_event(self, payload: Any) -> UnifiedJobEvent | None:
        """
        Map A's raw event payload to the unified JobEvent.
        Adjust this code to the real JSON structure of Warehouse A.
        """
        try:
            # Example payload shape (adapt to reality):
            # {
            #   "id": "...",
            #   "type": "job.created",
            #   "timestamp": "...",
            #   "data": { "job": { "id": "...", ... } }
            # }
            event_id = payload["id"]
            source_type = payload["type"]
            job = payload["data"]["job"]
            job_id = job["id"]

            if source_type == "job.created":
                ev_type = JobEventType.CREATED
            elif source_type == "job.updated":
                ev_type = JobEventType.UPDATED
            elif source_type == "job.deleted":
                ev_type = JobEventType.DELETED
            else:
                return None  # not a job event

            occurred_at = None
            if "timestamp" in payload:
                occurred_at = datetime.fromisoformat(raw["timestamp"])

            return JobEvent(
                event_id=event_id,
                job_id=job_id,
                type=ev_type,
                occurred_at=occurred_at,
                payload=payload,
                metadata={},
            )
        except Exception:
            return None

    def fetch_jobs_for_events(self, events: Iterable[UnifiedJob]) -> List[WarehouseAJob]:
        job_ids = [e.job_id for e in events]
        # Use your real client/requests to fetch jobs by ids
        return self.requests.fetch_jobs_by_ids(job_ids)

    def get_job_id(self, job: WarehouseAJob) -> str:
        return job.job_id

    # read_profiles_batch, _write_profiles_native, to_unified_profile, from_unified_profile similar...


# Optional: factory to build a default instance with some dummy auth
def _build_default_connector() -> WarehouseAConnector:
    auth = ApiKeyAuth("X-API-Key", "dummy")
    requests = WarehouseARequests(client=None)  # inject your real client
    return WarehouseAConnector(auth=auth, requests=requests)


#TODO define a @classmethod on WarehouseAConnector:
# @classmethod
# def build_default(cls) -> "WarehouseAConnector": ...
