# src/hrtech_etl/connectors/warehouse_a/models.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from hrtech_etl.core.models import UnifiedJobEvent, UnifiedProfileEvent
from hrtech_etl.core.types import Cursor, CursorMode, JobEventType, ProfileEventType


class WarehouseAJob(BaseModel):
    """
    Native job representation for Warehouse A.
    """

    job_id: str = Field(
        ...,
        json_schema_extra={
            # candidates for cursor modes
            "cursor": ["id"],
            # prefilter metadata (used by Prefilter + UI)
            "prefilter": {"operators": ["eq", "in", "contains"]},
        },
    )
    title: str = Field(
        ...,
        json_schema_extra={
            "prefilter": {"operators": ["eq", "contains"]},
        },
    )
    created_at: datetime = Field(
        ...,
        json_schema_extra={
            "cursor": ["created_at"],
            "prefilter": {"operators": ["gte", "lte"]},
        },
    )
    updated_at: datetime = Field(
        ...,
        json_schema_extra={
            "cursor": ["updated_at"],
            "prefilter": {"operators": ["gte", "lte"]},
        },
    )
    payload: Dict[str, Any] = {}


class WarehouseAProfile(BaseModel):
    """
    Native profile representation for Warehouse A.
    """

    profile_id: str = Field(
        ...,
        json_schema_extra={
            "cursor": ["id"],
            "prefilter": {"operators": ["eq", "in", "contains"]},
        },
    )
    full_name: str = Field(
        ...,
        json_schema_extra={
            "prefilter": {"operators": ["eq", "contains"]},
        },
    )
    created_at: datetime = Field(
        ...,
        json_schema_extra={
            "cursor": ["created_at"],
            "prefilter": {"operators": ["gte", "lte"]},
        },
    )
    updated_at: datetime = Field(
        ...,
        json_schema_extra={
            "cursor": ["updated_at"],
            "prefilter": {"operators": ["gte", "lte"]},
        },
    )
    payload: Dict[str, Any] = {}


# -------- Native event models (optional but handy) --------


class WarehouseAJobEvent(BaseModel):
    """
    Native job event for Warehouse A.

    Pattern:
    - parse payload payload (webhook / queue) with `from_payload`
    - convert to UnifiedJobEvent with `.to_unified()`
    """

    event_id: str
    job_id: str
    event_type: str
    timestamp: Optional[datetime] = None
    payload: Dict[str, Any]

    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> Optional["WarehouseAJobEvent"]:
        """
        Example mapping – adapt to real payload.

        Suppose Warehouse A sends:

        {
          "id": "...",
          "type": "job.created",
          "timestamp": "...",
          "data": { "job": { "id": "...", ... } }
        }
        """
        try:
            event_id = payload["id"]
            event_type = payload["type"]
            job_id = payload["data"]["job"]["id"]
            ts = payload.get("timestamp")
            timestamp = datetime.fromisoformat(ts) if ts else None

            return cls(
                event_id=event_id,
                job_id=job_id,
                event_type=event_type,
                timestamp=timestamp,
                payload=payload,
            )
        except Exception:
            # not a job event or malformed → ignore
            return None

    def to_unified(self) -> UnifiedJobEvent:
        if self.event_type == "job.created":
            event_type = JobEventType.CREATED
        elif self.event_type == "job.updated":
            event_type = JobEventType.UPDATED
        elif self.event_type == "job.deleted":
            event_type = JobEventType.DELETED
        else:
            event_type = JobEventType.UPSERTED

        cursor = Cursor(
            mode=CursorMode.ID,
            start=self.event_id,
            end=self.event_id,
        )

        return UnifiedJobEvent(
            event_id=self.event_id,
            job_id=self.job_id,
            type=event_type,
            occurred_at=self.timestamp,
            payload=self.payload,
            metadata={},
            cursor=cursor,
        )


class WarehouseAProfileEvent(BaseModel):
    """
    Native profile event for Warehouse A.
    """

    event_id: str
    profile_id: str
    event_type: str
    timestamp: Optional[datetime] = None
    payload: Dict[str, Any]

    @classmethod
    def from_payload(
        cls, payload: Dict[str, Any]
    ) -> Optional["WarehouseAProfileEvent"]:
        # Adjust to actual payload shape
        try:
            event_id = payload["id"]
            event_type = payload["type"]
            profile_id = payload["data"]["profile"]["id"]
            ts = payload.get("timestamp")
            timestamp = datetime.fromisoformat(ts) if ts else None

            return cls(
                event_id=event_id,
                profile_id=profile_id,
                event_type=event_type,
                timestamp=timestamp,
                payload=payload,
            )
        except Exception:
            return None

    def to_unified(self) -> UnifiedProfileEvent:
        if self.event_type == "profile.created":
            event_type = ProfileEventType.CREATED
        elif self.event_type == "profile.updated":
            event_type = ProfileEventType.UPDATED
        elif self.event_type == "profile.deleted":
            event_type = ProfileEventType.DELETED
        else:
            event_type = ProfileEventType.UPSERTED

        cursor = Cursor(
            mode=CursorMode.ID,
            start=self.event_id,
            end=self.event_id,
        )

        return UnifiedProfileEvent(
            event_id=self.event_id,
            profile_id=self.profile_id,
            type=event_type,
            occurred_at=self.timestamp,
            payload=self.payload,
            metadata={},
            cursor=cursor,
        )


# ----------------------------------------------
