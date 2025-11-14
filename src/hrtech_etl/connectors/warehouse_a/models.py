# src/hrtech_etl/connectors/warehouse_a/models.py
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class WarehouseAJob(BaseModel):
    """
    Native JOB model for Warehouse A.

    - Fields use json_schema_extra["cursor"] to indicate cursor role:
        "id"         -> ID-based cursor
        "created_at" -> created_at-based cursor
        "updated_at" -> updated_at-based cursor

    - json_schema_extra["filter"] encodes whether the field is usable in WHERE
      conditions and which operators are allowed.
    """

    job_id: str = Field(
        ...,
        json_schema_extra={
            "cursor": "id",
            "filter": {
                "eligible": True,
                "operators": ["eq", "in"],  # allowed operators for where clauses
            },
        },
    )

    job_title: str = Field(
        ...,
        json_schema_extra={
            "filter": {
                "eligible": True,
                "operators": ["eq", "contains"],
            },
        },
    )

    status: str = Field(
        "open",
        json_schema_extra={
            "filter": {
                "eligible": True,
                "operators": ["eq", "in"],
            },
        },
    )

    location: Optional[str] = Field(
        None,
        json_schema_extra={
            "filter": {
                "eligible": True,
                "operators": ["eq", "contains"],
            },
        },
    )

    last_modified: datetime = Field(
        ...,
        json_schema_extra={
            "cursor": "updated_at",
            "filter": {
                "eligible": True,
                "operators": ["eq", "gt", "gte", "lt", "lte"],
            },
        },
    )

    created_on: datetime = Field(
        ...,
        json_schema_extra={
            "cursor": "created_at",
            "filter": {
                "eligible": True,
                "operators": ["eq", "gt", "gte", "lt", "lte"],
            },
        },
    )

    # Arbitrary extra fields from the source system
    payload: Dict[str, Any] = Field(default_factory=dict)


class WarehouseAProfile(BaseModel):
    """
    Native PROFILE model for Warehouse A.
    Similar approach: cursor + filter metadata on relevant fields.
    """

    profile_id: str = Field(
        ...,
        json_schema_extra={
            "cursor": "id",
            "filter": {
                "eligible": True,
                "operators": ["eq", "in"],
            },
        },
    )

    full_name: str = Field(
        ...,
        json_schema_extra={
            "filter": {
                "eligible": True,
                "operators": ["eq", "contains"],
            },
        },
    )

    email: Optional[str] = Field(
        None,
        json_schema_extra={
            "filter": {
                "eligible": True,
                "operators": ["eq", "in", "contains"],
            },
        },
    )

    updated_time: datetime = Field(
        ...,
        json_schema_extra={
            "cursor": "updated_at",
            "filter": {
                "eligible": True,
                "operators": ["eq", "gt", "gte", "lt", "lte"],
            },
        },
    )

    created_time: datetime = Field(
        ...,
        json_schema_extra={
            "cursor": "created_at",
            "filter": {
                "eligible": True,
                "operators": ["eq", "gt", "gte", "lt", "lte"],
            },
        },
    )

    current_position: Optional[str] = Field(
        None,
        json_schema_extra={
            "filter": {
                "eligible": True,
                "operators": ["eq", "contains"],
            },
        },
    )

    payload: Dict[str, Any] = Field(default_factory=dict)
