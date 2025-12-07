# src/hrtech_etl/connectors/warehouse_a/models.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from datetime import datetime

from hrtech_etl.core.models import UnifiedJobEvent, UnifiedProfileEvent
from hrtech_etl.core.types import Cursor, CursorMode, JobEventType, ProfileEventType


# ---------------------------------------------------------------------------
# Native resources for Warehouse A
# ---------------------------------------------------------------------------


class WarehouseAJob(BaseModel):
    """
    Native job representation for Warehouse A.

    This model is used both:
      - as the "native_cls" for the connector
      - as the source/target for mapping-based formatters.
    """

    job_id: str = Field(
        ...,
        json_schema_extra={
            # Candidate for CursorMode.UID (id-based paging, events, etc.)
            "cursor": CursorMode.UID.value,
            "cursor_start_min": "job_id_min",
            "cursor_end_max": "job_id_max",
            "cursor_order_up": "asc",
            "cursor_order_down": "desc",
            # UI / Prefilter metadata
            "prefilter": {"operators": ["eq", "in", "contains"]},
        },
        description="Native identifier of the job in Warehouse A.",
    )

    title: str = Field(
        ...,
        json_schema_extra={
            "prefilter": {"operators": ["eq", "contains"]},
        },
        description="Job title as stored in Warehouse A.",
    )

    created_at: datetime = Field(
        ...,
        json_schema_extra={
            # Used for CursorMode.CREATED_AT
            "cursor": CursorMode.CREATED_AT.value,
            "cursor_start_min": "created_at_min",  # lower bound param
            "cursor_end_max": "created_at_max",    # upper bound param
            "cursor_order_up": "asc",
            "cursor_order_down": "desc",
            "prefilter": {"operators": ["gte", "lte"]},
        },
        description="Creation datetime of the job in Warehouse A.",
    )

    updated_at: datetime = Field(
        ...,
        json_schema_extra={
            # Used for CursorMode.UPDATED_AT
            "cursor": CursorMode.UPDATED_AT.value,
            "cursor_start_min": "updated_at_min",
            "cursor_end_max": "updated_at_max",
            "cursor_order_up": "asc",
            "cursor_order_down": "desc",
            "prefilter": {"operators": ["gte", "lte"]},
        },
        description="Last update datetime of the job in Warehouse A.",
    )

    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Raw extra data coming from Warehouse A.",
    )


class WarehouseAProfile(BaseModel):
    """
    Native profile representation for Warehouse A.
    """

    profile_id: str = Field(
        ...,
        json_schema_extra={
            "cursor": CursorMode.UID.value,
            "cursor_start_min": "profile_id_min",
            "cursor_end_max": "profile_id_max",
            "cursor_order_up": "asc",
            "cursor_order_down": "desc",
            "prefilter": {"operators": ["eq", "in", "contains"]},
        },
        description="Native identifier of the profile in Warehouse A.",
    )

    full_name: str = Field(
        ...,
        json_schema_extra={
            "prefilter": {"operators": ["eq", "contains"]},
        },
        description="Full name of the profile.",
    )

    created_at: datetime = Field(
        ...,
        json_schema_extra={
            "cursor": CursorMode.CREATED_AT.value,
            "cursor_start_min": "created_at_min",
            "cursor_end_max": "created_at_max",
            "cursor_order_up": "asc",
            "cursor_order_down": "desc",
            "prefilter": {"operators": ["gte", "lte"]},
        },
        description="Creation datetime of the profile in Warehouse A.",
    )

    updated_at: datetime = Field(
        ...,
        json_schema_extra={
            "cursor": CursorMode.UPDATED_AT.value,
            "cursor_start_min": "updated_at_min",
            "cursor_end_max": "updated_at_max",
            "cursor_order_up": "asc",
            "cursor_order_down": "desc",
            "prefilter": {"operators": ["gte", "lte"]},
        },
        description="Last update datetime of the profile in Warehouse A.",
    )

    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Raw extra data coming from Warehouse A.",
    )


# ---------------------------------------------------------------------------
# Native event models (optional but handy for webhook / queue integration)
# ---------------------------------------------------------------------------


class WarehouseAJobEvent(BaseModel):
    """
    Native job event for Warehouse A.

    Pattern:
      - parse webhook/queue payload with `from_payload`
      - convert to UnifiedJobEvent with `.to_unified()`
    """

    event_id: str
    job_id: str
    event_type: str
    timestamp: Optional[datetime] = None
    payload: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> Optional["WarehouseAJobEvent"]:
        """
        Example mapping – adapt to the real payload shape.

        Suppose Warehouse A sends something like:

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
            # Not a job event or malformed → ignore it upstream
            return None

    def to_unified(self) -> UnifiedJobEvent:
        """
        Convert this native event into a UnifiedJobEvent.
        """
        if self.event_type == "job.created":
            event_type = JobEventType.CREATED
        elif self.event_type == "job.updated":
            event_type = JobEventType.UPDATED
        elif self.event_type == "job.deleted":
            event_type = JobEventType.DELETED
        else:
            event_type = JobEventType.UPSERTED

        return UnifiedJobEvent(
            event_id=self.event_id,
            job_id=self.job_id,
            type=event_type,
            occurred_at=self.timestamp,
            payload=self.payload,
            metadata={},
        )


class WarehouseAProfileEvent(BaseModel):
    """
    Native profile event for Warehouse A.
    """

    event_id: str
    profile_id: str
    event_type: str
    timestamp: Optional[datetime] = None
    payload: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_payload(
        cls,
        payload: Dict[str, Any],
    ) -> Optional["WarehouseAProfileEvent"]:
        """
        Example mapping – adapt to the actual payload.

        Example:

        {
          "id": "...",
          "type": "profile.updated",
          "timestamp": "...",
          "data": { "profile": { "id": "...", ... } }
        }
        """
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
        """
        Convert this native event into a UnifiedProfileEvent.
        """
        if self.event_type == "profile.created":
            event_type = ProfileEventType.CREATED
        elif self.event_type == "profile.updated":
            event_type = ProfileEventType.UPDATED
        elif self.event_type == "profile.deleted":
            event_type = ProfileEventType.DELETED
        else:
            event_type = ProfileEventType.UPSERTED

        return UnifiedProfileEvent(
            event_id=self.event_id,
            profile_id=self.profile_id,
            type=event_type,
            occurred_at=self.timestamp,
            payload=self.payload,
            metadata={},
        )
