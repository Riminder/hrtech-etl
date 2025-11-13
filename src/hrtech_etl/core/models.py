# hrtech_etl/core/models.py
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class UnifiedJob(BaseModel):
    id: str
    title: str
    location: Optional[str] = None
    source: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    raw: Optional[Dict[str, Any]] = None


class UnifiedProfile(BaseModel):
    id: str
    full_name: str
    email: Optional[str] = None
    location: Optional[str] = None
    source: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    raw: Optional[Dict[str, Any]] = None
