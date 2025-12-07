# src/hrtech_etl/connectors/warehouse_a/__init__.py
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from pydantic import BaseModel
from datetime import datetime


from hrtech_etl.core.auth import ApiKeyAuth, BaseAuth
from hrtech_etl.core.connector import BaseConnector
from hrtech_etl.core.models import (
    UnifiedJob,
    UnifiedJobEvent,
    UnifiedProfile,
    UnifiedProfileEvent,
)
from hrtech_etl.core.registry import ConnectorMeta, register_connector
from hrtech_etl.core.types import Condition, Cursor, CursorMode, WarehouseType, Resource
from hrtech_etl.core.utils import build_connector_params, get_cursor_native_value

from .models import (
    WarehouseAJob,
    WarehouseAJobEvent,
    WarehouseAProfile,
    WarehouseAProfileEvent,
)
from .actions import WarehouseAActions


class WarehouseAConnector(BaseConnector):
    """
    Example connector for Warehouse A.

    - Owns the *semantic* logic:
        * how to build query params from (where, cursor) for this backend
        * how to map native <-> unified resources/events

    - Delegates low-level HTTP/DB calls to WarehouseAActions.
    """

    job_native_cls = WarehouseAJob
    profile_native_cls = WarehouseAProfile

    # How Warehouse A expects the sort parameter to be named (?order=created_at, etc.)
    sort_param_name = "order"

    def __init__(self, auth: BaseAuth, actions: WarehouseAActions):
        super().__init__(
            auth=auth,
            name="warehouse_a",
            warehouse_type=WarehouseType.JOBBOARD,
        )

    def _build_actions(self) -> WarehouseAActions:
        return WarehouseAActions(auth=self.auth)
    
    # ------------------------------------------------------------------
    # JOBS: unified ↔ native
    # ------------------------------------------------------------------

    def to_unified_job(self, native: BaseModel) -> UnifiedJob:
        """
        Map a native WarehouseAJob → UnifiedJob.

        ⚠ This is just an example mapping. Adapt it to your real UnifiedJob schema.
        """
        assert isinstance(native, WarehouseAJob)

        # Minimal example: id/key from job_id, name/title from title, dates from native.
        # Fill origin so you know where it comes from.
        return UnifiedJob(
            id=native.job_id,
            origin=self.name,
            key=native.job_id,
            reference=None,
            board_key="default_board",  # adapt to your real data
            board=None,
            created_at=native.created_at.isoformat() if native.created_at else None,
            updated_at=native.updated_at.isoformat() if native.updated_at else None,
            archived_at=None,
            name=native.title,
            summary=None,
            location=None,  # or some real Location if you have it
            url=None,
            text=native.title,
            sections=None,
            culture=None,
            benefits=None,
            responsibilities=None,
            requirements=None,
            interviews=None,
            skills=None,
            languages=None,
            tasks=None,
            certifications=None,
            courses=None,
            tags=None,
            metadatas=None,
            ranges_float=None,
            ranges_date=None,
            payload=native.payload,
        )

    def from_unified_job(self, unified: UnifiedJob) -> WarehouseAJob:
        """
        Map UnifiedJob → native WarehouseAJob.
        """
        # Fallbacks: use key or id if one is missing
        job_id = unified.id or unified.key

        return WarehouseAJob(
            job_id=job_id,
            title=unified.name or "",
            created_at=(
                # naive example: use updated_at if created_at is missing
                datetime.fromisoformat(unified.created_at)
                if unified.created_at
                else datetime.fromisoformat(unified.updated_at)
            ),
            updated_at=datetime.fromisoformat(unified.updated_at),
            payload=unified.payload or {},
        )

    def read_jobs_batch(
        self,
        where: List[Condition] | None,
        cursor: Cursor = Cursor(mode=CursorMode.UPDATED_AT, start=None, sort_by="asc"),
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
            resource_cls=WarehouseAJob,
            where=where,
            cursor=cursor,
            sort_by_unified=sort_by_unified,
            sort_param_name=self.sort_param_name,  # "order"
        )
        params["limit"] = batch_size

        jobs = self.actions.fetch_jobs(params=params)

        return self._finalize_read_batch(resources=jobs, cursor=cursor)

    def _write_jobs_native(self, jobs: List[BaseModel]) -> None:
        assert all(isinstance(j, WarehouseAJob) for j in jobs)
        self.actions.upsert_jobs(jobs)  # type: ignore[arg-type]

    def get_job_id(self, native_job: BaseModel) -> str:
        assert isinstance(native_job, WarehouseAJob)
        return native_job.job_id

    # ------------------------------------------------------------------
    # PROFILES: unified ↔ native
    # ------------------------------------------------------------------

    def to_unified_profile(self, native: BaseModel) -> UnifiedProfile:
        """
        Map a native WarehouseAProfile → UnifiedProfile.

        ⚠ Example mapping; adapt to your real UnifiedProfile schema.
        """
        assert isinstance(native, WarehouseAProfile)

        return UnifiedProfile(
            id=native.profile_id,
            origin=self.name,
            key=native.profile_id,
            reference=None,
            source_key="source_default",  # adapt
            created_at=native.created_at.isoformat() if native.created_at else None,
            updated_at=native.updated_at.isoformat() if native.updated_at else None,
            archived_at=None,
            info=None,  # or real ProfileInfo if you can build it
            text=native.full_name,
            text_language=None,
            experiences_duration=0.0,
            educations_duration=0.0,
            experiences=None,
            educations=None,
            attachments=[],
            skills=None,
            languages=None,
            tasks=None,
            certifications=None,
            courses=None,
            interests=None,
            tags=None,
            metadatas=None,
            labels=None,
            payload=native.payload,
        )

    def from_unified_profile(self, unified: UnifiedProfile) -> WarehouseAProfile:
        profile_id = unified.id or unified.key

        return WarehouseAProfile(
            profile_id=profile_id,
            full_name=(unified.info.full_name if unified.info else "") or "",
            created_at=(
                datetime.fromisoformat(unified.created_at)
                if unified.created_at
                else datetime.fromisoformat(unified.updated_at)
            ),
            updated_at=datetime.fromisoformat(unified.updated_at),
            payload=unified.payload or {},
        )

    def read_profiles_batch(
        self,
        where: List[Condition] | None,
        cursor: Cursor = Cursor(mode=CursorMode.UPDATED_AT, start=None, sort_by="asc"),
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
            resource_cls=WarehouseAProfile,
            where=where,
            cursor=cursor,
            sort_by_unified=sort_by_unified,
            sort_param_name=self.sort_param_name,  # "order"
        )
        params["limit"] = batch_size

        profiles = self.actions.fetch_profiles(params=params)

        return self._finalize_read_batch(resources=profiles, cursor=cursor)


    def _write_profiles_native(self, profiles: List[BaseModel]) -> None:
        assert all(isinstance(p, WarehouseAProfile) for p in profiles)
        self.actions.upsert_profiles(profiles)  # type: ignore[arg-type]

    def get_profile_id(self, native_profile: BaseModel) -> str:
        assert isinstance(native_profile, WarehouseAProfile)
        return native_profile.profile_id

    # ------------------------------------------------------------------
    # EVENTS: JOBS
    # ------------------------------------------------------------------

    def parse_job_event(self, raw: Any) -> UnifiedJobEvent | None:
        """
        Parse a raw payload (webhook / queue) into UnifiedJobEvent.
        """
        # In models.py we defined from_payload; adapt if you rename it.
        native_ev = WarehouseAJobEvent.from_payload(raw)
        if native_ev is None:
            return None
        return native_ev.to_unified()

    def fetch_jobs_by_events(
        self,
        events: Iterable[UnifiedJobEvent],
    ) -> List[BaseModel]:
        job_ids = [ev.job_id for ev in events]
        return self.actions.fetch_jobs_by_ids(job_ids)

    # ------------------------------------------------------------------
    # EVENTS: PROFILES
    # ------------------------------------------------------------------

    def parse_profile_event(self, raw: Any) -> UnifiedProfileEvent | None:
        native_ev = WarehouseAProfileEvent.from_payload(raw)
        if native_ev is None:
            return None
        return native_ev.to_unified()

    def fetch_profiles_by_events(
        self,
        events: Iterable[UnifiedProfileEvent],
    ) -> List[BaseModel]:
        profile_ids = [ev.profile_id for ev in events]
        return self.actions.fetch_profiles_by_ids(profile_ids)


# ----------------------------------------------------------------------
# Factory + Registry registration
# ----------------------------------------------------------------------


def _build_default_connector() -> WarehouseAConnector:
    """
    Convenience factory used by the registry / playground.

    In real life, you'd likely create this from env vars or a config file.
    """
    auth = ApiKeyAuth("X-API-Key", "dummy")
    actions = WarehouseAActions(
        base_url="https://api.warehouse-a.example",
        api_key="dummy",
    )
    return WarehouseAConnector(auth=auth, actions=actions)


register_connector(
    ConnectorMeta(
        name="warehouse_a",
        label="Warehouse A",
        warehouse_type=WarehouseType.JOBBOARD,
        job_model="hrtech_etl.connectors.warehouse_a.models.WarehouseAJob",
        profile_model="hrtech_etl.connectors.warehouse_a.models.WarehouseAProfile",
        connector_path="hrtech_etl.connectors.warehouse_a.WarehouseAConnector",
    ),
    factory=_build_default_connector,
)


__all__ = [
    "WarehouseAConnector",
    "WarehouseAJob",
    "WarehouseAProfile",
    "WarehouseAJobEvent",
    "WarehouseAProfileEvent",
    "WarehouseAActions",
]
