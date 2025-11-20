# src/hrtech_etl/connectors/warehouse_a/models.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from hrtech_etl.core.models import UnifiedJob, UnifiedProfile, UnifiedJobEvent, UnifiedProfileEvent
from hrtech_etl.core.types import Cursor, CursorMode, JobEventType, ProfileEventType


# --- JOBS ---

class WarehouseHrflowJob(UnifiedJob):
    ...  # Existing fields omitted for brevity


# --- NATIVE PROFILES ---

class WarehouseHrflowProfile(UnifiedProfile):
    ... # Existing fields omitted for brevity

# -------- Native event models (optional but handy) --------

#fixme fix fields according to webhooks
class WarehouseHrflowJobEvent(BaseModel):
    """
    Native job event for Warehouse HrFlow.ai.

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
    def from_payload(
        cls, payload: Dict[str, Any]
    ) -> Optional["WarehouseHrflowJobEvent"]:
        """
        Example mapping – adapt to real payload.

        Suppose Warehouse HrFlow.ai sends:

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
            mode=CursorMode.UID,
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

#fixme fix fields according to webhooks
class WarehouseHrflowProfileEvent(BaseModel):
    """
    Native profile event for Warehouse HrFlow.ai.
    """

    event_id: str
    profile_id: str
    event_type: str
    timestamp: Optional[datetime] = None
    payload: Dict[str, Any]

    @classmethod
    def from_payload(
        cls, payload: Dict[str, Any]
    ) -> Optional["WarehouseHrflowProfileEvent"]:
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
            mode=CursorMode.UID,
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
