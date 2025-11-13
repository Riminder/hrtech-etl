# hrtech_etl/connectors/warehouse_a/models.py
from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, Field


class WarehouseAJob(BaseModel):
    job_id: str = Field(..., json_schema_extra={"cursor": "id"})
    job_title: str
    last_modified: datetime = Field(..., json_schema_extra={"cursor": "updated_at"})
    created_on: datetime = Field(..., json_schema_extra={"cursor": "created_at"})
    payload: Dict[str, Any] = Field(default_factory=dict)


class WarehouseAProfile(BaseModel):
    profile_id: str = Field(..., json_schema_extra={"cursor": "id"})
    full_name: str
    updated_time: datetime = Field(..., json_schema_extra={"cursor": "updated_at"})
    created_time: datetime = Field(..., json_schema_extra={"cursor": "created_at"})
    payload: Dict[str, Any] = Field(default_factory=dict)
