# hrtech_etl/core/connector.py
from abc import ABC, abstractmethod
from typing import Any, List, Tuple, Optional, Type

from pydantic import BaseModel

from .auth import BaseAuth
from .models import UnifiedJob, UnifiedProfile
from .types import WarehouseType, CursorMode

Cursor = Optional[Any]


class BaseConnector(ABC):
    """
    Base class for all connectors (warehouses).

    job_native_cls / profile_native_cls MUST be Pydantic models.
    """

    job_native_cls: Type[BaseModel]
    profile_native_cls: Type[BaseModel]

    def __init__(self, auth: BaseAuth, name: str, warehouse_type: WarehouseType):
        self.auth = auth
        self.name = name
        self.warehouse_type = warehouse_type

    # --- JOBS ---

    @abstractmethod
    def read_jobs_batch(
        self,
        cursor: Cursor = None,
        cursor_mode: CursorMode = CursorMode.UPDATED_AT,
        batch_size: int = 1000,
    ) -> Tuple[List[BaseModel], Cursor]:
        ...

    @abstractmethod
    def _write_jobs_native(self, jobs: List[BaseModel]) -> None:
        ...

    @abstractmethod
    def to_unified_job(self, native: BaseModel) -> UnifiedJob:
        ...

    @abstractmethod
    def from_unified_job(self, unified: UnifiedJob) -> BaseModel:
        ...

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

    # --- PROFILES ---

    @abstractmethod
    def read_profiles_batch(
        self,
        cursor: Cursor = None,
        cursor_mode: CursorMode = CursorMode.UPDATED_AT,
        batch_size: int = 1000,
    ) -> Tuple[List[BaseModel], Cursor]:
        ...

    @abstractmethod
    def _write_profiles_native(self, profiles: List[BaseModel]) -> None:
        ...

    @abstractmethod
    def to_unified_profile(self, native: BaseModel) -> UnifiedProfile:
        ...

    @abstractmethod
    def from_unified_profile(self, unified: UnifiedProfile) -> BaseModel:
        ...

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
