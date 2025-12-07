from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from pydantic import BaseModel

from hrtech_etl.core.auth import ApiKeyAuth, BaseAuth
from hrtech_etl.core.connector import BaseConnector
from hrtech_etl.core.models import (
    UnifiedJob,
    UnifiedJobEvent,
    UnifiedProfile,
    UnifiedProfileEvent,
)
from hrtech_etl.core.registry import ConnectorMeta, register_connector
from hrtech_etl.core.types import Condition, Cursor, CursorMode, WarehouseType
from hrtech_etl.core.utils import build_connector_params

from .actions import WarehouseHrflowActions
from .models import (
    WarehouseHrflowJob,
    WarehouseHrflowJobEvent,
    WarehouseHrflowProfile,
    WarehouseHrflowProfileEvent,
)


class WarehouseHrflowConnector(BaseConnector):
    job_native_cls = WarehouseHrflowJob
    profile_native_cls = WarehouseHrflowProfile

    def __init__(self, auth: BaseAuth, actions: WarehouseHrflowActions) -> None:
        super().__init__(
            auth=auth,
            name="warehouse_hrflow",
            warehouse_type=WarehouseType.CUSTOMERS,
            actions=actions,
        )

    # -------- JOBS: unified ↔ native --------

    def to_unified_job(self, native: BaseModel) -> UnifiedJob:
        assert isinstance(native, WarehouseHrflowJob)
        return UnifiedJob(
            job_id=native.key,
            title=native.name,
            created_at=native.created_at,
            updated_at=native.updated_at,
            payload=native.payload,
            metadata={
                "connector": self.name,
                "warehouse_type": self.warehouse_type.value,
            },
        )

    def from_unified_job(self, unified: UnifiedJob) -> WarehouseHrflowJob:
        return WarehouseHrflowJob(
            key=unified.job_id,
            reference=unified.job_id,
            name=unified.title or "",
            created_at=unified.created_at or unified.updated_at,
            updated_at=unified.updated_at or unified.created_at,
            payload=unified.payload,
        )

    def read_jobs_batch(
        self,
        cursor: Cursor = Cursor(mode=CursorMode.UPDATED_AT, start=None, sort_by="asc"),
        where: list[Condition] | None = None,
        batch_size: int = 1000,
    ) -> Tuple[List[BaseModel], Optional[str]]:
        """
        High-level read for jobs:

          - builds query params (EQ / IN / search / cursor) using WarehouseAJob metadata
          - delegates actual HTTP call to actions.fetch_jobs(params)
        """
        where = where or []

        # Unified sort_by is typically the unified cursor field name.
        # For simplicity, we use cursor.mode.value ("updated_at", "created_at", "uid").
        sort_by_unified = cursor.mode.value

        params: Dict[str, Any] = build_connector_params(
            resource_cls=WarehouseHrflowJob,
            where=where,
            cursor=cursor,
            sort_by_unified=sort_by_unified,
            sort_param_name=self.sort_param_name,  # "order"
        )
        params["limit"] = batch_size

        jobs, next_cursor = self.actions.fetch_jobs(params=params)
        return jobs, next_cursor

    def _write_jobs_native(self, jobs: List[BaseModel]) -> None:
        assert all(isinstance(j, WarehouseHrflowJob) for j in jobs)
        self.actions.upsert_jobs(jobs)  # type: ignore[arg-type]

    def get_job_id(self, native_job: BaseModel) -> str:
        assert isinstance(native_job, WarehouseHrflowJob)
        return native_job.job_id

    # -------- PROFILES: unified ↔ native --------

    def to_unified_profile(self, native: BaseModel) -> UnifiedProfile:
        assert isinstance(native, WarehouseHrflowProfile)
        # FIXME: requires core update to align WarehouseHrflowProfile <-> UnifiedProfile
        return UnifiedProfile(
            profile_id=native.key,
            full_name=native.info.full_name,
            created_at=native.created_at,
            updated_at=native.updated_at,
            payload=native.payload,
            metadata={
                "connector": self.name,
                "warehouse_type": self.warehouse_type.value,
            },
        )

    def from_unified_profile(self, unified: UnifiedProfile) -> WarehouseHrflowProfile:
        # FIXME: requires core update to align WarehouseHrflowProfile <-> UnifiedProfile
        return WarehouseHrflowProfile(
            key=unified.profile_id,
            reference=unified.profile_id,
            created_at=unified.created_at or unified.updated_at,
            updated_at=unified.updated_at or unified.created_at,
            payload=unified.payload,
        )

    def read_profiles_batch(
        self,
        cursor: Cursor = Cursor(mode=CursorMode.UPDATED_AT, start=None, sort_by="asc"),
        where: list[Condition] | None = None,
        batch_size: int = 1000,
    ) -> Tuple[List[BaseModel], Optional[str]]:
        """
        High-level read for profiles:

          - builds query params (EQ / IN / search / cursor) using WarehouseAProfile metadata
          - delegates to actions.fetch_profiles(params)
        """
        where = where or []

        sort_by_unified = cursor.mode.value

        params: Dict[str, Any] = build_connector_params(
            resource_cls=WarehouseHrflowProfile,
            where=where,
            cursor=cursor,
            sort_by_unified=sort_by_unified,
            sort_param_name=self.sort_param_name,  # "order"
        )
        params["limit"] = batch_size

        profiles, next_cursor = self.actions.fetch_profiles(params=params)
        return profiles, next_cursor

    def _write_profiles_native(self, profiles: List[BaseModel]) -> None:
        assert all(isinstance(p, WarehouseHrflowProfile) for p in profiles)
        self.actions.upsert_profiles(profiles)  # type: ignore[arg-type]


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
        return self.actions.fetch_jobs_by_ids(job_ids)

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
        return self.actions.fetch_profiles_by_ids(profile_ids)


# ---------- Factory + Registry registration ----------


def _build_default_connector() -> WarehouseHrflowConnector:
    """
    Default factory mostly used by the Playground / tests.
    Replace dummy values with env-driven config when wiring for real.
    """
    # Question: why do we have the redundant api key usage ?
    auth = ApiKeyAuth("X-API-Key", "dummy_api_key")
    actions = WarehouseHrflowActions(
        base_url="https://api.hrflow.ai/v1",
        api_key="dummy_api_key",
        api_user_email="dummy@example.com",
        provider_key="dummy_board_key",
    )
    return WarehouseHrflowConnector(auth=auth, actions=actions)


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
    "WarehouseHrflowActions",
]
