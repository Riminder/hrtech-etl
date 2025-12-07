from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from hrtech_etl.core.models import (
    Attachment,
    Board,
    Education,
    Experience,
    GeneralEntitySchema,
    Label,
    Location,
    ProfileInfo,
    RangesDate,
    RangesFloat,
    Section,
    Skill,
    UnifiedJobEvent,
    UnifiedProfileEvent,
)
from hrtech_etl.core.types import BoolJoin, CursorMode, JobEventType, ProfileEventType

# ---------------------------------------------------------------------------
# Native resources for Warehouse HrFlow.ai
# ---------------------------------------------------------------------------


class WarehouseHrflowJob(BaseModel):
    id: Optional[str] = Field(description="Unique identifier of the Job.")
    key: str = Field(
        ...,
        json_schema_extra={
            "prefilter": {"operators": ["eq"]},
        },
        description="Identification key of the Job.",
    )
    reference: Optional[str] = Field(
        None,
        json_schema_extra={
            "prefilter": {"operators": ["eq"]},
        },
        description="Custom identifier of the Job.",
    )
    board_key: str = Field(
        ...,
        json_schema_extra={
            "prefilter": {"operators": ["in"]},
            "in_binding": {
                "query_field": "board_keys",
                "formatter": "array_string",
            },
        },
        description="Identification key of the Board attached to the Job.",
    )
    board: Optional[Board]  # FIXME: is this obsolete ?
    created_at: Optional[str] = Field(
        ...,
        json_schema_extra={
            "cursor": CursorMode.CREATED_AT.value,
            "cursor_start_min": "date_range_min",
            "cursor_end_max": "date_range_max",
            "cursor_order_up": "asc",
            "cursor_order_down": "desc",
            "prefilter": {"operators": ["gte", "lte"]},
        },
        description="type: datetime ISO8601, Creation date of the Job.",
    )
    updated_at: str = Field(
        ...,
        json_schema_extra={
            "cursor": CursorMode.UPDATED_AT.value,
            "cursor_start_min": "date_range_min",
            "cursor_end_max": "date_range_max",
            "cursor_order_up": "asc",
            "cursor_order_down": "desc",
            "prefilter": {"operators": ["gte", "lte"]},
        },
        description="type: datetime ISO8601, Last update date of the Job.",
    )
    archived_at: Optional[str] = Field(
        None,
        description=(
            "type: datetime ISO8601, Archive date of the Job. "
            "The value is null for unarchived Jobs."
        ),
    )
    name: str = Field(
        ...,
        json_schema_extra={
            "prefilter": {"operators": ["contains"]},
            "search_binding": {
                "search_field": "keywords",
                # How this group combines with other groups (title, summary, etc.)
                "field_join": BoolJoin.AND,  # => (name) OR (skills
                "value_join": BoolJoin.OR,  # => name1 OR name2 OR name3...
            },
        },
        description="Job title.",
    )
    summary: Optional[str] = Field(None, description="Brief summary of the Job.")
    location: Location = Field(..., description="Job location object.")
    url: Optional[str] = Field(None, description="Job post original URL.")
    text: str = Field(
        ...,
        description="Full text of the Job..",
        json_schema_extra={
            "search_binding": {
                "search_field": "keywords",
                # How this group combines with other groups (title, summary, etc.)
                "field_join": BoolJoin.AND,  # => (text) AND (skills...)
                "value_join": BoolJoin.OR,  # => text1 OR text2 OR text3...
            },
        },
    )
    sections: List[Section] = Field(
        None, description="Job custom sections."
    )  # FIXME: deprecation in progress
    culture: Optional[str] = Field(
        None, description="Describes the company's values, work environment, and ethos."
    )
    benefits: Optional[str] = Field(
        None, description="Lists the perks and advantages offered to employees."
    )
    responsibilities: Optional[str] = Field(
        None, description="Outlines the duties and tasks expected from the role."
    )
    requirements: Optional[str] = Field(
        None,
        description="Specifies the qualifications and skills needed for the position.",
    )
    interviews: Optional[str] = Field(
        None, description="Provides information about the interview process and stages."
    )
    skills: Optional[List[Skill]] = Field(
        None, description="List of skills of the Job."
    )
    languages: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of spoken languages of the Job"
    )
    tasks: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of tasks of the Job"
    )
    certifications: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of certifications of the Job."
    )
    courses: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of courses of the Job"
    )
    tags: Optional[List[GeneralEntitySchema]] = Field(
        None,
        description="List of tags of the Job.",
        json_schema_extra={
            "prefilter": {"operators": ["in"]},
            "in_binding": {
                "query_field": "tags",
                "formatter": "array_string",
            },
        },
    )
    metadatas: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of metadatas of the Job"
    )
    ranges_float: Optional[List[RangesFloat]] = Field(
        None, description="List of ranges of floats"
    )
    ranges_date: Optional[List[RangesDate]] = Field(
        None, description="List of ranges of dates"
    )


class WarehouseHrflowProfile(BaseModel):
    id: Optional[str] = Field(description="Unique identifier of the Job.")
    key: str = Field(
        ...,
        json_schema_extra={
            "prefilter": {"operators": ["eq"]},
        },
        description="Identification key of the Profile.",
    )
    reference: Optional[str] = Field(
        None,
        json_schema_extra={
            "prefilter": {"operators": ["eq"]},
        },
        description="Custom identifier of the Profile.",
    )
    source_key: str = Field(
        ...,
        json_schema_extra={
            "prefilter": {"operators": ["in"]},
            "in_binding": {
                "query_field": "source_keys",
                "formatter": "array_string",
            },
        },
    )
    created_at: str = Field(
        ...,
        json_schema_extra={
            "cursor": CursorMode.CREATED_AT.value,
            "cursor_start_min": "date_range_min",
            "cursor_end_max": "date_range_max",
            "cursor_order_up": "asc",
            "cursor_order_down": "desc",
            "prefilter": {"operators": ["gte", "lte"]},
        },
        description="type: datetime ISO8601, Creation date of the Profile.",
    )
    updated_at: str = Field(
        ...,
        json_schema_extra={
            "cursor": CursorMode.UPDATED_AT.value,
            "cursor_start_min": "date_range_min",
            "cursor_end_max": "date_range_max",
            "cursor_order_up": "asc",
            "cursor_order_down": "desc",
            "prefilter": {"operators": ["gte", "lte"]},
        },
        description="type: datetime ISO8601, Last update date of the Profile.",
    )
    archived_at: Optional[str] = Field(
        None,
        description=(
            "type: datetime ISO8601, Archive date of the Profile."
            " The value is null for unarchived Profiles."
        ),
    )
    info: ProfileInfo = Field(..., description="Object containing the Profile's info.")
    text: str = Field(
        ...,
        description="Full text of the Profile..",
        json_schema_extra={
            "prefilter": {"operators": ["contains"]},
            "search_binding": {
                "search_field": "keywords",
                # How this group combines with other groups (title, summary, etc.)
                "field_join": BoolJoin.AND,  # => (text) AND (skills...)
                "value_join": BoolJoin.OR,  # => text1 OR text2 OR text3...
            },
        },
    )
    text_language: Optional[str] = Field(
        None, description="Code language of the Profile. type: string code ISO 639-1"
    )
    experiences_duration: float = Field(
        None, description="Total number of years of experience."
    )
    educations_duration: float = Field(
        None, description="Total number of years of education."
    )
    experiences: Optional[List[Experience]] = Field(
        None, description="List of experiences of the Profile."
    )
    educations: Optional[List[Education]] = Field(
        None, description="List of educations of the Profile."
    )
    attachments: List[Attachment] = Field(
        None, description="List of documents attached to the Profile."
    )
    skills: Optional[List[Skill]] = Field(
        None,
        description="List of skills of the Profile.",
    )
    languages: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of spoken languages of the profile"
    )
    tasks: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of tasks of the Profile."
    )
    certifications: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of certifications of the Profile."
    )
    courses: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of courses of the Profile."
    )
    interests: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of interests of the Profile."
    )
    tags: Optional[List[GeneralEntitySchema]] = Field(
        None,
        description="List of tags of the Profile.",
        json_schema_extra={
            "prefilter": {"operators": ["in"]},
            "in_binding": {
                "query_field": "tags",  # query field name
                "formatter": "array",  # which formatter to use from .utils.formatters
            },
        },
    )
    metadatas: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of metadatas of the Profile."
    )
    labels: Optional[List[Label]] = Field(
        None, description="List of labels of the Profile."
    )


# ---------------------------------------------------------------------------
# Native event models (optional but handy for webhook / queue integration)
# ---------------------------------------------------------------------------


class WarehouseHrflowJobEvent(BaseModel):
    """
    Native job event for Warehouse HrFlow.ai.

    Pattern:
    - parse payload payload (webhook / queue) with `from_payload`
    - convert to UnifiedJobEvent with `.to_unified()`
    """

    # FIXME: check missing parameters
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


class WarehouseHrflowProfileEvent(BaseModel):
    """
    Native profile event for Warehouse HrFlow.ai.
    """

    # FIXME: check missing parameters
    event_id: str
    profile_id: str
    event_type: str
    timestamp: Optional[datetime] = None
    payload: Dict[str, Any]

    @classmethod
    def from_payload(
        cls, payload: Dict[str, Any]
    ) -> Optional["WarehouseHrflowProfileEvent"]:
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
