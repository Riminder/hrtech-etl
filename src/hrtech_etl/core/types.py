# hrtech_etl/core/types.py
from enum import Enum
from typing import Any, Callable
from enum import Enum
from pydantic import BaseModel


FilterFn = Callable[[Any], bool]


class WarehouseType(str, Enum):
    ATS = "ats"
    CRM = "crm"
    JOBBOARD = "jobboard"
    HCM = "hcm"


class CursorMode(str, Enum):
    UPDATED_AT = "updated_at"
    CREATED_AT = "created_at"
    ID = "id"


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