# hrtech_etl/core/types.py
from enum import Enum
from typing import Any, Callable


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
