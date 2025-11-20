# src/hrtech_etl/connectors/warehouse_a/__init__.py
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from pydantic import BaseModel

from hrtech_etl.core.auth import ApiKeyAuth, BaseAuth
from hrtech_etl.core.connector import BaseConnector
from hrtech_etl.core.models import (
    UnifiedJob,
    UnifiedJobEvent,
    UnifiedProfile,
    UnifiedProfileEvent
)
from hrtech_etl.core.registry import ConnectorMeta, register_connector
from hrtech_etl.core.types import Condition, Cursor, CursorMode, WarehouseType
from hrtech_etl.core.utils import (
    get_cursor_native_name,
    build_eq_query_params, 
    build_search_query_params)

from .models import (
    WarehouseAJob,
    WarehouseAJobEvent,
    WarehouseAProfile,
    WarehouseAProfileEvent,
)
from .actions import WarehouseAActions


class WarehouseAConnector(BaseConnector):
    job_native_cls = WarehouseAJob
    profile_native_cls = WarehouseAProfile

    def __init__(self, auth: BaseAuth, actions: WarehouseAActions):
        super().__init__(
            auth=auth,
            name="warehouse_a",
            warehouse_type=WarehouseType.JOBBOARD,  # ou ATS / CRM / HCM
            actions=actions,
        )

    # -------- JOBS: unified ↔ native --------

    def to_unified_job(self, native: BaseModel) -> UnifiedJob:
        assert isinstance(native, WarehouseAJob)
        return UnifiedJob(
            job_id=native.id,
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
            job_id=unified.id,
            title=unified.title or "",
            created_at=unified.created_at or unified.updated_at,
            updated_at=unified.updated_at or unified.created_at,
            payload=unified.payload,
        )

    def read_jobs_batch(
        self,
        where: list[Condition] | None,
        cursor: Cursor = Cursor(mode=CursorMode.UPDATED_AT, start=None, sort_by="asc"),
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

        jobs, next_cursor = self.actions.fetch_jobs(
            cursor=cursor,
            where=where_payload,
            limit=batch_size,
        )
        return jobs, next_cursor

    def _write_jobs_native(self, jobs: List[BaseModel]) -> None:
        assert all(isinstance(j, WarehouseAJob) for j in jobs)
        self.actions.upsert_jobs(jobs)  # type: ignore[arg-type]


    def get_job_id(self, native_job: BaseModel) -> str:
        assert isinstance(native_job, WarehouseAJob)
        return native_job.id

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
            profile_id=unified.id,
            full_name=unified.full_name or "",
            created_at=unified.created_at or unified.updated_at,
            updated_at=unified.updated_at or unified.created_at,
            payload=unified.payload,
        )

    def read_profiles_batch(
        self,
        where: list[Condition] | None,
        cursor: Cursor = Cursor(mode=CursorMode.UPDATED_AT, start=None, sort_by="asc"),
        batch_size: int = 1000,
    ) -> Tuple[List[BaseModel], Optional[str]]:
        where_payload: Dict[str, Any] | None = None

        if where:
            where_payload = {}
            for cond in where:
                if cond.op.value == "eq":
                    where_payload[cond.field] = cond.value

        profiles, next_cursor = self.actions.fetch_profiles(
            cursor=cursor,
            where=where_payload,
            limit=batch_size,
        )
        return profiles, next_cursor

    def _write_profiles_native(self, profiles: List[BaseModel]) -> None:
        assert all(isinstance(p, WarehouseAProfile) for p in profiles)
        self.actions.upsert_profiles(profiles)  # type: ignore[arg-type]


    def get_profile_id(self, native_profile: BaseModel) -> str:
        assert isinstance(native_profile, WarehouseAProfile)
        return native_profile.id

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
        return self.actions.fetch_jobs_by_ids(job_ids)

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
        return self.actions.fetch_profiles_by_ids(profile_ids)

    # --- WHERE FILTER HELPERS ---
    def build_connector_query_params(
        self,
        resource: BaseModel,
        cursor: Cursor=Cursor(mode=CursorMode.UPDATED_AT, start=None, sort_by="asc"),
        where: Optional[List[Condition]]=None,
        order_by_name: Optional[str] = "sort_by",
        order_by_value: Optional[str] = "asc",
        batch_size: int = 1000,
    ) -> Dict[str, Any]:
        """
        Build connector-specific query params from generic WHERE conditions + cursor.
        """
        cursor_name = get_cursor_native_name(resource, cursor.mode)
        cursor_param = {}
        if cursor_name and cursor.start is not None:
            cursor_param = {cursor_name: cursor.start}  
        sort_param = {order_by_name: order_by_value} if order_by_name else {}
        base_params = build_eq_query_params(where)
        search_params = build_search_query_params(where=where, resource=resource)
        return {**base_params, **search_params, **cursor_param, **sort_param}  # search params override if same key
    
# ---------- Factory + Registry registration ----------


# Optional: factory to build a default instance with some dummy auth
def _build_default_connector() -> WarehouseAConnector:
    auth = ApiKeyAuth("X-API-Key", "dummy")
    # adapte à la signature actuelle de WarehouseAActions
    actions = WarehouseAActions(
        base_url="https://api.warehouse-a.example",
        api_key="dummy",
    )
    return WarehouseAConnector(auth=auth, actions=actions)


# Register for UI / config usage
register_connector(
    ConnectorMeta(
        name="warehouse_a",
        label="Warehouse A",
        warehouse_type=WarehouseType.JOBBOARD,
        job_model="hrtech_etl.connectors.warehouse_a.models.WarehouseAJob",
        profile_model="hrtech_etl.connectors.warehouse_a.models.WarehouseAProfile",
    ),
    factory=_build_default_connector,  # 👈 important
)


__all__ = [
    "WarehouseAConnector",
    "WarehouseAJob",
    "WarehouseAProfile",
    "WarehouseAJobEvent",
    "WarehouseAProfileEvent",
    "WarehouseAActions",
]
