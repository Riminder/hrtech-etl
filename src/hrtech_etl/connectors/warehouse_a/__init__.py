# hrtech_etl/connectors/warehouse_a/__init__.py
from typing import List, Tuple, Optional, Any
from datetime import datetime

from ...core.connector import BaseConnector, Cursor
from ...core.auth import BaseAuth
from ...core.types import WarehouseType, CursorMode
from ...core.models import UnifiedJob, UnifiedProfile
from .models import WarehouseAJob, WarehouseAProfile
from .actions import WarehouseAActions

from hrtech_etl.core.registry import register_connector, ConnectorMeta


from hrtech_etl.core.registry import register_connector, ConnectorMeta
from hrtech_etl.core.types import WarehouseType


# Optional: factory to build a default instance with some dummy auth
def _build_default_connector() -> WarehouseAConnector:
    from hrtech_etl.core.auth import ApiKeyAuth
    auth = ApiKeyAuth("X-API-Key", "dummy")
    actions = WarehouseAActions(client=None)  # inject your real client
    return WarehouseAConnector(auth=auth, actions=actions)


#TODO define a @classmethod on WarehouseAConnector:
# @classmethod
# def build_default(cls) -> "WarehouseAConnector": ...


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

    def __init__(self, auth: BaseAuth, actions: WarehouseAActions):
        super().__init__(
            auth=auth,
            name="warehouse_a",
            warehouse_type=WarehouseType.JOBBOARD,
        )
        self.actions = actions

    def read_jobs_batch(
        self,
        cursor: Cursor = None,
        cursor_mode: CursorMode = CursorMode.UPDATED_AT,
        batch_size: int = 1000,
    ) -> Tuple[List[WarehouseAJob], Cursor]:
        # interpret cursor depending on mode
        if cursor_mode == CursorMode.UPDATED_AT:
            updated_after: Optional[datetime] = cursor
            jobs = self.actions.fetch_jobs(updated_after=updated_after, limit=batch_size)
        elif cursor_mode == CursorMode.CREATED_AT:
            created_after: Optional[datetime] = cursor
            jobs = self.actions.fetch_jobs(created_after=created_after, limit=batch_size)
        elif cursor_mode == CursorMode.ID:
            id_after: Optional[str] = cursor
            jobs = self.actions.fetch_jobs(id_after=id_after, limit=batch_size)
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

    # read_profiles_batch, _write_profiles_native, to_unified_profile, from_unified_profile similar...
