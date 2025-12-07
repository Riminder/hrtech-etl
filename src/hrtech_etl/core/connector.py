# hrtech_etl/core/connector.py
from abc import ABC, abstractmethod
from typing import Any, Iterable, List, Optional, Tuple, Type, Dict

from pydantic import BaseModel

from .auth import BaseAuth
from .models import UnifiedJob, UnifiedJobEvent, UnifiedProfile, UnifiedProfileEvent
from .types import Condition, CursorMode, Resource, WarehouseType, Cursor, Operator
from .utils import (
    build_cursor_query_params,
    build_eq_query_params, 
    build_search_query_params,
    get_cursor_native_value
)

class BaseConnector(ABC):
    """
    One connector per external system (ATS / CRM / Jobboard / HCM).
    Handles jobs, profiles, and their unified conversions.
    """

    # Native Pydantic models for this warehouse
    job_native_cls: Type[BaseModel]
    profile_native_cls: Type[BaseModel]
    # nom du param HTTP pour le tri (connecteur-spécifique)
    sort_param_name: Optional[str] = None  # ex: "order" ou "sort_by"

    # --- AUTH / INIT ---

    def __init__(
        self,
        auth: BaseAuth,
        name: str,
        warehouse_type: WarehouseType,
        actions: BaseModel,
    ):
        self.auth = auth
        self.name = name
        self.warehouse_type = warehouse_type
        self.actions = actions



    # --- JOBS PRIMITIVES: READ / WRITE / CURSOR ---

    @abstractmethod
    def to_unified_job(self, native: BaseModel) -> UnifiedJob:
        """Convert native job → UnifiedJob."""
        raise NotImplementedError

    @abstractmethod
    def from_unified_job(self, unified: UnifiedJob) -> BaseModel:
        """Convert UnifiedJob → native job."""
        raise NotImplementedError

    @abstractmethod
    def read_jobs_batch(
        self,
        cursor: Cursor = Cursor(mode=CursorMode.UPDATED_AT, start=None, sort_by="asc"),
        where: list[Condition] | None = None,
        batch_size: int = 1000,
    ) -> Tuple[List[BaseModel], Optional[str]]:
        """
        Read a batch of native jobs with optional pre-filter (WHERE) and cursor.
        Returns (jobs, next_cursor).
        """
        raise NotImplementedError

    @abstractmethod
    def _write_jobs_native(self, jobs: List[BaseModel]) -> None:
        """
        Write/upsert a batch of native jobs into this warehouse.
        """
        raise NotImplementedError

    # not abstractmethod
    def write_jobs_batch(self, jobs: List[Any]) -> None:
        if not jobs:
            return

        first = jobs[0]

        if isinstance(first, UnifiedJob):
            native_jobs = [self.from_unified_job(j) for j in jobs]
            self._write_jobs_native(native_jobs)
        elif isinstance(first, self.job_native_cls):
            self._write_jobs_native(jobs)
        else:
            raise TypeError(
                f"[{self.name}] Unsupported job type {type(first)} "
                f"(expected {self.job_native_cls} or UnifiedJob)."
            )

    @abstractmethod
    def get_job_id(self, native_job: BaseModel) -> str:
        """Extract business job_id from a native job."""
        raise NotImplementedError

    # --- PROFILES: READ / WRITE / CURSOR ---

    @abstractmethod
    def to_unified_profile(self, native: BaseModel) -> UnifiedProfile:
        """Convert native profile → UnifiedProfile."""
        raise NotImplementedError

    @abstractmethod
    def from_unified_profile(self, unified: UnifiedProfile) -> BaseModel:
        """Convert UnifiedProfile → native profile."""
        raise NotImplementedError

    @abstractmethod
    def read_profiles_batch(
        self,
        cursor: Cursor = Cursor(mode=CursorMode.UPDATED_AT, start=None, sort_by="asc"),
        where: list[Condition] | None = None,
        batch_size: int = 1000,
    ) -> Tuple[List[BaseModel], Optional[str]]:
        """
        Read a batch of native profiles with optional pre-filter (WHERE) and cursor.
        Returns (profiles, next_cursor).
        """
        raise NotImplementedError

    @abstractmethod
    def _write_profiles_native(self, profiles: List[BaseModel]) -> None:
        """
        Write/upsert a batch of native profiles into this warehouse.
        """
        raise NotImplementedError

    # not abstractmethod
    def write_profiles_batch(self, profiles: List[Any]) -> None:
        if not profiles:
            return

        first = profiles[0]

        if isinstance(first, UnifiedProfile):
            native_profiles = [self.from_unified_profile(p) for p in profiles]
            self._write_profiles_native(native_profiles)
        elif isinstance(first, self.profile_native_cls):
            self._write_profiles_native(profiles)
        else:
            raise TypeError(
                f"[{self.name}] Unsupported profile type {type(first)} "
                f"(expected {self.profile_native_cls} or UnifiedProfile)."
            )

    @abstractmethod
    def get_profile_id(self, native_profile: BaseModel) -> str:
        raise NotImplementedError

    # --- EVENTS: JOBS ---

    def parse_job_event(self, raw: Any) -> UnifiedJobEvent | None:
        """
        Default: connector may override to interpret its own event payloads
        and produce a unified JobEvent.

        Return None if the event is not a job event or should be ignored.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement parse_job_event"
        )

    def fetch_jobs_by_events(
        self, events: Iterable[UnifiedJobEvent]
    ) -> List[BaseModel]:
        """
        Given unified JobEvent objects (with job_id), fetch native jobs.
        Override per connector depending on how you query jobs by id(s).
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement fetch_jobs_by_events"
        )

    # --- EVENTS: PROFILES ---

    def parse_profile_event(self, raw: Any) -> UnifiedProfileEvent | None:
        """
        Default: connector may override to interpret its own event payloads
        and produce a unified ProfileEvent.

        Return None if the event is not a profile event or should be ignored.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement parse_profile_event"
        )

    def fetch_profiles_by_events(
        self, events: Iterable[UnifiedProfileEvent]
    ) -> List[BaseModel]:
        """
        Given unified ProfileEvent objects (with profile_id), fetch native profiles.
        Override per connector depending on how you query profiles by id(s).
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement fetch_profiles_by_events"
        )

    # -------- GENERIC RESOURCE HELPERS (used by core) --------
    # Resources: JOB / PROFILE
    def read_resources_batch(
        self,
        resource: Resource,
        cursor: Cursor=Cursor(mode=CursorMode.UPDATED_AT, start=None, sort_by="asc"),
        where: list[Condition] | None = None,
        batch_size: int=1000,
    ) -> Tuple[List[BaseModel], Optional[str]]:
        if resource == Resource.JOB:
            return self.read_jobs_batch(
                cursor=cursor,
                where=where,
                batch_size=batch_size,
            )
        elif resource == Resource.PROFILE:
            return self.read_profiles_batch(
                cursor=cursor,
                where=where,
                batch_size=batch_size,
            )
        else:
            raise ValueError(f"Unsupported resource: {resource}")
    
    def _finalize_read_batch(
        self,
        resources: List[BaseModel],
        cursor: Cursor,
    ) -> Tuple[List[BaseModel], Optional[str]]:
        """
        Shared helper for read_resources_batch implementations.

        Behavior:
          - If no items were returned:
              * return an empty list
              * keep the previous cursor.start as next_cursor (no progress)
          - Else:
              * compute next_cursor from the last item using cursor.mode
              * return (items, next_cursor)
        """
        if not resources:
            # No data but we keep current start as the "last known" cursor
            return [], cursor.start

        next_cursor = get_cursor_native_value(
            resource=resources[-1],      # last native object of the batch
            cursor_mode=cursor.mode, # which field to use (id / created_at / updated_at)
        )
        return resources, next_cursor

    def write_resources_batch(
        self,
        resource: Resource,
        resources: List[Any],
    ) -> None:
        if resource == Resource.JOB:
            self.write_jobs_batch(resources)
        elif resource == Resource.PROFILE:
            self.write_profiles_batch(resources)
        else:
            raise ValueError(f"Unsupported resource: {resource}")

    def get_resource_id(
        self,
        resource: Resource,
        native_resource: BaseModel,
    ) -> str:
        if resource == Resource.JOB:
            return self.get_job_id(native_resource)
        elif resource == Resource.PROFILE:
            return self.get_profile_id(native_resource)
        else:
            raise ValueError(f"Unsupported resource: {resource}")

    # --- GENERIC EVENT HELPERS ---

    def parse_resource_event(
        self,
        resource: Resource,
        payload: Any,
    ) -> UnifiedJobEvent | UnifiedProfileEvent | None:
        """
        Parse event payload into unified event depending on resource type.
        - Resource.JOB: parse_job_event
        - Resource.PROFILE: parse_profile_event
        """
        if resource == Resource.JOB:
            return self.parse_job_event(payload)
        elif resource == Resource.PROFILE:
            return self.parse_profile_event(payload)
        else:
            raise ValueError(
                f"Unsupported resource in parse_resource_event: {resource}"
            )

    def fetch_resources_by_events(
        self,
        resource: Resource,
        events: Iterable[UnifiedJobEvent] | Iterable[UnifiedProfileEvent],
    ) -> List[BaseModel]:
        """
        Fetch native resources by unified events depending on resource type.
        - Resource.JOB: fetch_jobs_by_events
        - Resource.PROFILE: fetch_profiles_by_events
        """
        if resource == Resource.JOB:
            return self.fetch_jobs_by_events(events)  # type: ignore
        elif resource == Resource.PROFILE:
            return self.fetch_profiles_by_events(events)  # type: ignore
        else:
            raise ValueError(
                f"Unsupported resource in fetch_resources_by_events: {resource}"
            )
    