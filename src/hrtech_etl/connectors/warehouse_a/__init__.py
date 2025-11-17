# src/hrtech_etl/connectors/warehouse_a/__init__.py
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from pydantic import BaseModel

from hrtech_etl.core.auth import BaseAuth, ApiKeyAuth
from hrtech_etl.core.connector import BaseConnector
from hrtech_etl.core.models import (
    UnifiedJob,
    UnifiedProfile,
    UnifiedJobEvent,
    UnifiedProfileEvent,
)
from hrtech_etl.core.types import (
    WarehouseType,
    CursorMode,
    Condition,
)
from hrtech_etl.core.registry import register_connector, ConnectorMeta

from .models import (
    WarehouseAJob,
    WarehouseAProfile,
    WarehouseAJobEvent,
    WarehouseAProfileEvent,
)
from .requests import WarehouseARequests


class WarehouseAConnector(BaseConnector):
    job_native_cls = WarehouseAJob
    profile_native_cls = WarehouseAProfile

    def __init__(self, auth: BaseAuth, requests: WarehouseARequests):
        super().__init__(
            auth=auth,
            name="warehouse_a",
            warehouse_type=WarehouseType.JOBBOARD,  # ou ATS / CRM / HCM
            requests=requests,
        )

    # -------- JOBS: unified ↔ native --------

    def to_unified_job(self, native: BaseModel) -> UnifiedJob:
        assert isinstance(native, WarehouseAJob)
        return UnifiedJob(
            job_id=native.job_id,
            title=native.title,
            created_at=native.created_at,
            updated_at=native.updated_at,
            payload=native.payload,
            metadata={
                "connector": self.name,
                "warehouse_type": self.warehouse_type.value,
            },
        )

    def from_unified_job(self, unified: UnifiedJob) -> WarehouseAJob:
        return WarehouseAJob(
            job_id=unified.job_id,
            title=unified.title or "",
            created_at=unified.created_at or unified.updated_at,
            updated_at=unified.updated_at or unified.created_at,
            payload=unified.payload,
        )

    def read_jobs_batch(
        self,
        where: list[Condition] | None,
        cursor_start: Optional[str] = None,
        cursor_mode: CursorMode = CursorMode.UPDATED_AT,
        batch_size: int = 1000,
    ) -> Tuple[List[BaseModel], Optional[str]]:
        where_payload: Dict[str, Any] | None = None

        if where:
            where_payload = {}
            for cond in where:
                # Exemple simple : EQ -> égalité
                if cond.op.value == "eq":
                    where_payload[cond.field] = cond.value
                # TODO: mapper gte/lte/contains → syntaxe de l’API A

        jobs, next_cursor = self.requests.fetch_jobs(
            where=where_payload,
            cursor_start=cursor_start,
            cursor_mode=cursor_mode.value,
            limit=batch_size,
        )
        return jobs, next_cursor

    def _write_jobs_native(self, jobs: List[BaseModel]) -> None:
        assert all(isinstance(j, WarehouseAJob) for j in jobs)
        self.requests.upsert_jobs(jobs)  # type: ignore[arg-type]

    def get_cursor_from_native_job(
        self, native_job: BaseModel, cursor_mode: CursorMode
    ) -> Optional[str]:
        assert isinstance(native_job, WarehouseAJob)
        if cursor_mode == CursorMode.ID:
            return native_job.job_id
        if cursor_mode == CursorMode.CREATED_AT:
            return native_job.created_at.isoformat()
        if cursor_mode == CursorMode.UPDATED_AT:
            return native_job.updated_at.isoformat()
        return None

    def get_job_id(self, native_job: BaseModel) -> str:
        assert isinstance(native_job, WarehouseAJob)
        return native_job.job_id

    # -------- PROFILES: unified ↔ native --------

    def to_unified_profile(self, native: BaseModel) -> UnifiedProfile:
        assert isinstance(native, WarehouseAProfile)
        return UnifiedProfile(
            profile_id=native.profile_id,
            full_name=native.full_name,
            created_at=native.created_at,
            updated_at=native.updated_at,
            payload=native.payload,
            metadata={
                "connector": self.name,
                "warehouse_type": self.warehouse_type.value,
            },
        )

    def from_unified_profile(self, unified: UnifiedProfile) -> WarehouseAProfile:
        return WarehouseAProfile(
            profile_id=unified.profile_id,
            full_name=unified.full_name or "",
            created_at=unified.created_at or unified.updated_at,
            updated_at=unified.updated_at or unified.created_at,
            payload=unified.payload,
        )

    def read_profiles_batch(
        self,
        where: list[Condition] | None,
        cursor_start: Optional[str] = None,
        cursor_mode: CursorMode = CursorMode.UPDATED_AT,
        batch_size: int = 1000,
    ) -> Tuple[List[BaseModel], Optional[str]]:
        where_payload: Dict[str, Any] | None = None

        if where:
            where_payload = {}
            for cond in where:
                if cond.op.value == "eq":
                    where_payload[cond.field] = cond.value

        profiles, next_cursor = self.requests.fetch_profiles(
            where=where_payload,
            cursor_start=cursor_start,
            cursor_mode=cursor_mode.value,
            limit=batch_size,
        )
        return profiles, next_cursor

    def _write_profiles_native(self, profiles: List[BaseModel]) -> None:
        assert all(isinstance(p, WarehouseAProfile) for p in profiles)
        self.requests.upsert_profiles(profiles)  # type: ignore[arg-type]

    def get_cursor_from_native_profile(
        self, native_profile: BaseModel, cursor_mode: CursorMode
    ) -> Optional[str]:
        assert isinstance(native_profile, WarehouseAProfile)
        if cursor_mode == CursorMode.ID:
            return native_profile.profile_id
        if cursor_mode == CursorMode.CREATED_AT:
            return native_profile.created_at.isoformat()
        if cursor_mode == CursorMode.UPDATED_AT:
            return native_profile.updated_at.isoformat()
        return None

    def get_profile_id(self, native_profile: BaseModel) -> str:
        assert isinstance(native_profile, WarehouseAProfile)
        return native_profile.profile_id

    # -------- EVENTS: JOBS --------

    def parse_job_event(self, raw: Any) -> UnifiedJobEvent | None:
        native_ev = WarehouseAJobEvent.from_raw(raw)
        if native_ev is None:
            return None
        return native_ev.to_unified()

    def fetch_jobs_by_events(
        self, events: Iterable[UnifiedJobEvent]
    ) -> List[BaseModel]:
        job_ids = [ev.job_id for ev in events]
        return self.requests.fetch_jobs_by_ids(job_ids)

    # -------- EVENTS: PROFILES --------

    def parse_profile_event(self, raw: Any) -> UnifiedProfileEvent | None:
        native_ev = WarehouseAProfileEvent.from_raw(raw)
        if native_ev is None:
            return None
        return native_ev.to_unified()

    def fetch_profiles_by_events(
        self, events: Iterable[UnifiedProfileEvent]
    ) -> List[BaseModel]:
        profile_ids = [ev.profile_id for ev in events]
        return self.requests.fetch_profiles_by_ids(profile_ids)


# ---------- Factory + Registry registration ----------

# Optional: factory to build a default instance with some dummy auth
def _build_default_connector() -> WarehouseAConnector:
    auth = ApiKeyAuth("X-API-Key", "dummy")
    # adapte à la signature actuelle de WarehouseARequests
    requests = WarehouseARequests(
        base_url="https://api.warehouse-a.example",
        api_key="dummy",
    )
    return WarehouseAConnector(auth=auth, requests=requests)



# Register for UI / config usage
register_connector(
    ConnectorMeta(
        name="warehouse_a",
        label="Warehouse A",
        warehouse_type=WarehouseType.JOBBOARD,
        job_model="hrtech_etl.connectors.warehouse_a.models.WarehouseAJob",
        profile_model="hrtech_etl.connectors.warehouse_a.models.WarehouseAProfile",
    ),
    factory=_build_default_connector,   # 👈 important
)


__all__ = [
    "WarehouseAConnector",
    "WarehouseAJob",
    "WarehouseAProfile",
    "WarehouseAJobEvent",
    "WarehouseAProfileEvent",
    "WarehouseARequests",
]
