# hrtech_etl/core/models.py
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from .types import JobEventType, ProfileEventType, Cursor, CursorMode


class UnifiedJob(BaseModel):
    id: str
    title: str
    location: Optional[str] = None
    source: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    raw: Optional[Dict[str, Any]] = None


class UnifiedJobEvent(BaseModel):
    event_id: str
    job_id: str
    type: JobEventType
    occurred_at: Optional[datetime] = None
    payload: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}
    cursor: Cursor = Field(
        default_factory=lambda: Cursor(mode=CursorMode.ID)
    )


class UnifiedProfile(BaseModel):
    id: str
    full_name: str
    email: Optional[str] = None
    location: Optional[str] = None
    source: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    raw: Optional[Dict[str, Any]] = None


class UnifiedProfileEvent(BaseModel):
    event_id: str
    profile_id: str
    type: ProfileEventType
    occurred_at: Optional[datetime] = None
    payload: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}
    cursor: Cursor = Field(
        default_factory=lambda: Cursor(mode=CursorMode.ID)
    )