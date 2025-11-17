# hrtech_etl/core/types.py
from enum import Enum
from typing import Any, Callable, Dict, Optional, Union

from pydantic import BaseModel


class Resource(str, Enum):
    JOB = "job"
    PROFILE = "profile"


Formatter = Optional[Callable[[BaseModel], Union[BaseModel, Dict[str, Any]]]]


class WarehouseType(str, Enum):
    ATS = "ats"
    CRM = "crm"
    JOBBOARD = "jobboard"
    HCM = "hcm"
    CUSTOMERS = "customers"


class CursorMode(str, Enum):
    ID = "id"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


class Cursor(BaseModel):
    mode: CursorMode
    start: Optional[str] = None  # input
    end: Optional[str] = None  # output (filled by pipeline)


class Operator(str, Enum):
    EQ = "eq"
    GT = "gt"
    LT = "lt"
    GTE = "gte"
    LTE = "lte"
    IN = "in"
    CONTAINS = "contains"


class Condition(BaseModel):
    field: str
    op: Operator
    value: Any


class JobEventType(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    ARCHIVED = "archived"
    UPSERTED = "upserted"  # created or updated


class ProfileEventType(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    ARCHIVED = "archived"
    UPSERTED = "upserted"  # created or updated


class PushMode(str, Enum):
    EVENTS = "events"  # push job/profile events
    RESOURCES = "resources"  # e.g., jobs, profiles #todo change to items


class PushResult(BaseModel):
    total_events: int = 0
    total_resources_fetched: int = 0
    total_resources_pushed: int = 0
    skipped_missing: int = 0
    skipped_having: int = 0
    errors: list[str] = []
