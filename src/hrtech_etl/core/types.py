# hrtech_etl/core/types.py
from enum import Enum
from typing import Any,Optional
from enum import Enum
from pydantic import BaseModel


class WarehouseType(str, Enum):
    ATS = "ats"
    CRM = "crm"
    JOBBOARD = "jobboard"
    HCM = "hcm"


class CursorMode(str, Enum):
    ID = "id"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


class Cursor(BaseModel):
    mode: CursorMode
    start: Optional[str] = None  # input
    end: Optional[str] = None    # output (filled by pipeline)


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