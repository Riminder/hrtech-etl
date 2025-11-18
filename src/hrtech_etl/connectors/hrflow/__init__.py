from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from pydantic import BaseModel

from hrtech_etl.core.auth import BaseAuth
from hrtech_etl.core.connector import BaseConnector
from hrtech_etl.core.models import (
    UnifiedJob,
    UnifiedJobEvent,
    UnifiedProfile,
    UnifiedProfileEvent,
)
from hrtech_etl.core.registry import ConnectorMeta, register_connector
from hrtech_etl.core.types import Condition, CursorMode, WarehouseType

from .actions import WarehouseHrflowRequests
from .auth import HrFlowAuth
from .models import (
    WarehouseHrflowJob,
    WarehouseHrflowJobEvent,
    WarehouseHrflowProfile,
    WarehouseHrflowProfileEvent,
)


class WarehouseHrflowConnector(BaseConnector):
    job_native_cls = WarehouseHrflowJob
    profile_native_cls = WarehouseHrflowProfile

    def __init__(self, auth: BaseAuth, requests: WarehouseHrflowRequests) -> None:
        # FIXME: warehouse type doesn't fit
        super().__init__(
            auth=auth,
            name="warehouse_hrflow",
            warehouse_type=WarehouseType.CUSTOMERS,
            requests=requests,
        )

    # -------- JOBS: unified ↔ native --------

    def to_unified_job(self, native: BaseModel) -> UnifiedJob:
        assert isinstance(native, WarehouseHrflowJob)
        return UnifiedJob(
            job_id=native.job_id,
            title=native.title,
            created_at=native.created_at,
            updated_at=native.updated_at,
            payload=native.payload,  # Question: je n'ai pas compris
            metadata={
                "connector": self.name,
                "warehouse_type": self.warehouse_type.value,
            },
        )

    def from_unified_job(self, unified: UnifiedJob) -> WarehouseHrflowJob:
        return WarehouseHrflowJob(
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
        assert all(isinstance(j, WarehouseHrflowJob) for j in jobs)
        self.requests.upsert_jobs(jobs)  # type: ignore[arg-type]

    def get_cursor_from_native_job(
        self, native_job: BaseModel, cursor_mode: CursorMode
    ) -> Optional[str]:
        assert isinstance(native_job, WarehouseHrflowJob)
        if cursor_mode == CursorMode.ID:
            return native_job.job_id
        if cursor_mode == CursorMode.CREATED_AT:
            return native_job.created_at.isoformat()
        if cursor_mode == CursorMode.UPDATED_AT:
            return native_job.updated_at.isoformat()
        return None

    def get_job_id(self, native_job: BaseModel) -> str:
        assert isinstance(native_job, WarehouseHrflowJob)
        return native_job.job_id

    # -------- PROFILES: unified ↔ native --------

    def to_unified_profile(self, native: BaseModel) -> UnifiedProfile:
        assert isinstance(native, WarehouseHrflowProfile)
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

    def from_unified_profile(self, unified: UnifiedProfile) -> WarehouseHrflowProfile:
        return WarehouseHrflowProfile(
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
        assert all(isinstance(p, WarehouseHrflowProfile) for p in profiles)
        self.requests.upsert_profiles(profiles)  # type: ignore[arg-type]

    def get_cursor_from_native_profile(
        self, native_profile: BaseModel, cursor_mode: CursorMode
    ) -> Optional[str]:
        assert isinstance(native_profile, WarehouseHrflowProfile)
        if cursor_mode == CursorMode.ID:
            return native_profile.profile_id
        if cursor_mode == CursorMode.CREATED_AT:
            return native_profile.created_at.isoformat()
        if cursor_mode == CursorMode.UPDATED_AT:
            return native_profile.updated_at.isoformat()
        return None

    def get_profile_id(self, native_profile: BaseModel) -> str:
        assert isinstance(native_profile, WarehouseHrflowProfile)
        return native_profile.profile_id

    # -------- EVENTS: JOBS --------

    def parse_job_event(self, raw: Any) -> UnifiedJobEvent | None:
        native_ev = WarehouseHrflowJobEvent.from_raw(raw)
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
        native_ev = WarehouseHrflowProfileEvent.from_raw(raw)
        if native_ev is None:
            return None
        return native_ev.to_unified()

    def fetch_profiles_by_events(
        self, events: Iterable[UnifiedProfileEvent]
    ) -> List[BaseModel]:
        profile_ids = [ev.profile_id for ev in events]
        return self.requests.fetch_profiles_by_ids(profile_ids)


# ---------- Factory + Registry registration ----------


def _build_default_connector() -> WarehouseHrflowConnector:
    """
    Default factory mostly used by the Playground / tests.
    Replace dummy values with env-driven config when wiring for real.
    """
    auth = HrFlowAuth(
        api_key="dummy_api_key",
        user_email="dummy@example.com",
    )
    requests = WarehouseHrflowRequests(
        base_url="https://api.hrflow.ai/v1",
        auth=auth,
        board_key="dummy_board_key",
        source_key=None,  # or a dummy profile source if you like
    )
    return WarehouseHrflowConnector(auth=auth, requests=requests)


# Register for UI / config usage
register_connector(
    ConnectorMeta(
        name="warehouse_hrflow",
        label="Warehouse HrFlow.ai",
        warehouse_type=WarehouseType.CUSTOMERS,
        job_model="hrtech_etl.connectors.warehouse_hrflow.models.WarehouseHrflowJob",
        profile_model=(
            "hrtech_etl.connectors." "warehouse_hrflow.models.WarehouseHrflowProfile"
        ),
        connector_path=(
            "hrtech_etl.connectors." "warehouse_hrflow.WarehouseHrflowConnector"
        ),
    ),
    factory=_build_default_connector,  # 👈 important
)


__all__ = [
    "WarehouseHrflowConnector",
    "WarehouseHrflowJob",
    "WarehouseHrflowProfile",
    "WarehouseHrflowJobEvent",
    "WarehouseHrflowProfileEvent",
    "WarehouseHrflowRequests",
]
