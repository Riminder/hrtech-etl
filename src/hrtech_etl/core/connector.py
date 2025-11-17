# hrtech_etl/core/connector.py
from abc import ABC, abstractmethod
from typing import Any, List, Tuple, Optional, Type, Iterable

from pydantic import BaseModel

from .auth import BaseAuth
from .models import UnifiedJob, UnifiedProfile, UnifiedJobEvent, UnifiedProfileEvent
from .types import Resource, WarehouseType, CursorMode, Condition


class BaseConnector(ABC):
    """
    One connector per external system (ATS / CRM / Jobboard / HCM).
    Handles jobs, profiles, and their unified conversions.
    """

    # Native Pydantic models for this warehouse
    job_native_cls: Type[BaseModel]
    profile_native_cls: Type[BaseModel]

    # --- AUTH / INIT ---

    def __init__(self, auth: BaseAuth, name: str, warehouse_type: WarehouseType, requests: BaseModel):
        self.auth = auth
        self.name = name
        self.warehouse_type = warehouse_type
        self.requests = requests
    
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
        where: list[Condition] | None,
        cursor_start: str = None, #fixme starting cursor 
        cursor_mode: CursorMode = CursorMode.UPDATED_AT,
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
    def get_cursor_from_native_job(
        self, native_job: BaseModel, cursor_mode: CursorMode
    ) -> str | None:
        """Extract cursor value from a native job."""
        raise NotImplementedError

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
        where: list[Condition] | None,
        cursor_start: str = None,
        cursor_mode: CursorMode = CursorMode.UPDATED_AT,
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
    def get_cursor_from_native_profile(
        self, native_profile: BaseModel, cursor_mode: CursorMode
    ) -> str | None:
        raise NotImplementedError

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

    def fetch_jobs_by_events(self, events: Iterable[UnifiedJobEvent]) -> List[BaseModel]:
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
    
    def fetch_profiles_by_events(self, events: Iterable[UnifiedProfileEvent]) -> List[BaseModel]:
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
        where: list[Condition] | None,
        cursor_start: Optional[str],
        cursor_mode: CursorMode,
        batch_size: int,
    ) -> Tuple[List[BaseModel], Optional[str]]:
        if resource == Resource.JOB:
            return self.read_jobs_batch(
                where=where,
                cursor_start=cursor_start,
                cursor_mode=cursor_mode,
                batch_size=batch_size,
            )
        elif resource == Resource.PROFILE:
            return self.read_profiles_batch(
                where=where,
                cursor_start=cursor_start,
                cursor_mode=cursor_mode,
                batch_size=batch_size,
            )
        else:
            raise ValueError(f"Unsupported resource: {resource}")

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

    def get_cursor_from_native_resource(
        self,
        resource: Resource,
        native_resource: BaseModel,
        cursor_mode: CursorMode,
    ) -> Optional[str]:
        if resource == Resource.JOB:
            return self.get_cursor_from_native_job(native_resource, cursor_mode)
        elif resource == Resource.PROFILE:
            return self.get_cursor_from_native_profile(native_resource, cursor_mode)
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
            raise ValueError(f"Unsupported resource in parse_resource_event: {resource}")

    def fetch_resources_by_events(
        self,
        resource: Resource,
        events: Iterable[UnifiedJobEvent] | Iterable[UnifiedProfileEvent],
    ) -> List[BaseModel]:
        if resource == Resource.JOB:
            return self.fetch_jobs_by_events(events)  # type: ignore
        elif resource == Resource.PROFILE:
            return self.fetch_profiles_by_events(events)  # type: ignore
        else:
            raise ValueError(f"Unsupported resource in fetch_resources_by_events: {resource}")

   