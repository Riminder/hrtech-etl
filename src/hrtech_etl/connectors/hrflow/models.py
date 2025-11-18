# src/hrtech_etl/connectors/warehouse_a/models.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from hrtech_etl.core.models import UnifiedJobEvent, UnifiedProfileEvent
from hrtech_etl.core.types import Cursor, CursorMode, JobEventType, ProfileEventType


class LocationFields(BaseModel):
    category: Optional[str]
    city: Optional[str]
    city_district: Optional[str]
    country: Optional[str]
    country_region: Optional[str]
    entrance: Optional[str]
    house: Optional[str]
    house_number: Optional[str]
    island: Optional[str]
    level: Optional[str]
    near: Optional[str]
    po_box: Optional[str]
    postcode: Optional[str]
    road: Optional[str]
    staircase: Optional[str]
    state: Optional[str]
    state_district: Optional[str]
    suburb: Optional[str]
    text: Optional[str]
    unit: Optional[str]
    world_region: Optional[str]


class Location(BaseModel):
    text: Optional[str] = Field(None, description="Location text address.")
    lat: Optional[float] = Field(
        None, description="Geocentric latitude of the Location."
    )
    lng: Optional[float] = Field(
        None, description="Geocentric longitude of the Location."
    )
    _fields: Optional[LocationFields] = Field(
        None,
        alias="fields",
        description="Other location attributes like country, country_code etc",
    )


class GeneralEntitySchema(BaseModel):
    name: str = Field(..., description="Identification name of the Object")
    value: Optional[str] = Field(
        None, description="Value associated to the Object's name"
    )


class Label(BaseModel):
    board_key: str = Field(
        ..., description="Identification key of the Board attached to the Job."
    )
    job_key: str = Field(None, description="Identification key of the Job.")
    job_reference: Optional[str] = Field(
        None, description="Custom identifier of the Job."
    )
    stage: str = Field(..., description="Stage of the job")
    date_stage: str = Field(..., description="Date when the job reached this stage")
    rating: int = Field(..., description="Rating associated with the job")
    date_rating: str = Field(..., description="Date when the rating was given")


class Skill(BaseModel):
    name: str = Field(..., description="Identification name of the skill")
    type: Optional[str] = Field(None, description="Type of the skill. hard or soft")
    value: Optional[str] = Field(None, description="Value associated to the skill")


# --- JOBS ---


class Section(BaseModel):
    name: Optional[str] = Field(
        None,
        description="Identification name of a Section of the Job. Example: culture",
    )
    title: Optional[str] = Field(
        None, description="Display Title of a Section. Example: Corporate Culture"
    )
    description: Optional[str] = Field(
        None, description="Text description of a Section: Example: Our values areNone"
    )


class RangesFloat(BaseModel):
    name: Optional[str] = Field(
        None,
        description=(
            "Identification name of a Range of floats attached "
            "to the Job. Example: salary"
        ),
    )
    value_min: Optional[float] = Field(None, description="Min value. Example: 500.")
    value_max: Optional[float] = Field(None, description="Max value. Example: 100.")
    unit: Optional[str] = Field(None, description="Unit of the value. Example: euros.")


class RangesDate(BaseModel):
    name: Optional[str] = Field(
        None,
        description=(
            "Identification name of a Range of dates attached"
            " to the Job. Example: availability."
        ),
    )
    value_min: Optional[str] = Field(
        None, description="Min value in datetime ISO 8601, Example: 500."
    )
    value_max: Optional[str] = Field(
        None, description="Max value in datetime ISO 8601, Example: 1000"
    )


class Board(BaseModel):
    key: str = Field(..., description="Identification key of the Board.")
    name: str = Field(..., description="Name of the Board.")
    type: str = Field(..., description="Type of the Board, Example: api, folder")
    subtype: str = Field(
        ..., description="Subtype of the Board, Example: python, excel"
    )
    environment: str = Field(
        ..., description="Environment of the Board, Example: production, staging, test"
    )


class WarehouseHrflowJob(BaseModel):
    key: str = Field(
        ...,
        json_schema_extra={
            "prefilter": {"operators": ["eq", "in", "contains"]},
        },
        description="Identification key of the Job.",
    )
    reference: Optional[str] = Field(
        None,
        json_schema_extra={
            "prefilter": {"operators": ["eq", "in", "contains"]},
        },
        description="Custom identifier of the Job.",
    )
    name: str = Field(
        ...,
        json_schema_extra={
            "prefilter": {"operators": ["eq", "contains"]},
        },
        description="Job title.",
    )
    board_key: str = Field(
        ...,
        json_schema_extra={
            "prefilter": {"operators": ["eq", "in", "contains"]},
        },
        description="Identification key of the Board attached to the Job.",
    )
    location: Location = Field(..., description="Job location object.")
    sections: List[Section] = Field(None, description="Job custom sections.")
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
    url: Optional[str] = Field(None, description="Job post original URL.")
    summary: Optional[str] = Field(None, description="Brief summary of the Job.")
    board: Optional[Board]
    archived_at: Optional[str] = Field(
        None,
        description=(
            "type: datetime ISO8601, Archive date of the Job. "
            "The value is null for unarchived Jobs."
        ),
    )
    updated_at: str = Field(
        ...,
        json_schema_extra={
            "cursor": ["updated_at"],
            "prefilter": {"operators": ["gte", "lte"]},
        },
        description="type: datetime ISO8601, Last update date of the Job.",
    )
    created_at: Optional[str] = Field(
        ...,
        json_schema_extra={
            "cursor": ["created_at"],
            "prefilter": {"operators": ["gte", "lte"]},
        },
        description="type: datetime ISO8601, Creation date of the Job.",
    )
    skills: Optional[List[Skill]] = Field(
        None, description="List of skills of the Job."
    )
    languages: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of spoken languages of the Job"
    )
    certifications: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of certifications of the Job."
    )
    courses: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of courses of the Job"
    )
    tasks: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of tasks of the Job"
    )
    tags: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of tags of the Job"
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
    payload: Dict[str, Any] = {}


# --- PROFILES ---


class Url(BaseModel):
    type: Optional[Literal["from_resume", "linkedin", "twitter", "facebook", "github"]]
    url: Optional[str]


class ProfileInfo(BaseModel):
    full_name: Optional[str] = Field(
        None,
        json_schema_extra={
            "prefilter": {"operators": ["eq", "contains"]},
        },
        description="Profile full name",
    )
    first_name: Optional[str] = Field(None, description="Profile first name")
    last_name: Optional[str] = Field(None, description="Profile last name")
    email: Optional[str] = Field(None, description="Profile email")
    phone: Optional[str] = Field(None, description="Profile phone number")
    date_birth: Optional[str] = Field(None, description="Profile date of birth")
    location: Optional[Location] = Field(None, description="Profile location object")
    urls: Optional[List[Url]] = Field(
        None, description="Profile social networks and URLs"
    )
    picture: Optional[str] = Field(None, description="Profile picture url")
    gender: Optional[str] = Field(None, description="Profile gender")
    summary: Optional[str] = Field(None, description="Profile summary text")


class Experience(BaseModel):
    key: Optional[str] = Field(
        None, description="Identification key of the Experience."
    )
    company: Optional[str] = Field(None, description="Company name of the Experience.")
    logo: Optional[str] = Field(None, description="Logo of the Company.")
    title: Optional[str] = Field(None, description="Title of the Experience.")
    description: Optional[str] = Field(
        None, description="Description of the Experience."
    )
    location: Optional[Location] = Field(
        None, description="Location object of the Experience."
    )
    date_start: Optional[str] = Field(
        None, description="Start date of the experience. type: ('datetime ISO 8601')"
    )
    date_end: Optional[str] = Field(
        None, description="End date of the experience. type: ('datetime ISO 8601')"
    )
    skills: Optional[List[Skill]] = Field(
        None, description="List of skills of the Experience."
    )
    certifications: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of certifications of the Experience."
    )
    courses: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of courses of the Experience."
    )
    tasks: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of tasks of the Experience."
    )
    languages: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of spoken languages of the profile"
    )
    interests: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of interests of the Experience."
    )


class Education(BaseModel):
    key: Optional[str] = Field(None, description="Identification key of the Education.")
    school: Optional[str] = Field(None, description="School name of the Education.")
    logo: Optional[str] = Field(None, description="Logo of the School.")
    title: Optional[str] = Field(None, description="Title of the Education.")
    description: Optional[str] = Field(
        None, description="Description of the Education."
    )
    location: Optional[Location] = Field(
        None, description="Location object of the Education."
    )
    date_start: Optional[str] = Field(
        None, description="Start date of the Education. type: ('datetime ISO 8601')"
    )
    date_end: Optional[str] = Field(
        None, description="End date of the Education. type: ('datetime ISO 8601')"
    )
    skills: Optional[List[Skill]] = Field(
        None, description="List of skills of the Education."
    )
    certifications: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of certifications of the Education."
    )
    courses: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of courses of the Education."
    )
    tasks: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of tasks of the Education."
    )
    languages: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of spoken languages of the profile"
    )
    interests: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of interests of the Experience."
    )


class Attachment(BaseModel):
    type: Optional[str]
    alt: Optional[str]
    file_size: Optional[str]
    file_name: Optional[str]
    original_file_name: Optional[str]
    extension: Optional[str]
    public_url: Optional[str]
    updated_at: Optional[str]
    created_at: Optional[str]


class WarehouseHrflowProfile(BaseModel):
    key: str = Field(
        ...,
        json_schema_extra={
            "prefilter": {"operators": ["eq", "in", "contains"]},
        },
        description="Identification key of the Profile.",
    )
    reference: Optional[str] = Field(
        None,
        json_schema_extra={
            "prefilter": {"operators": ["eq", "in", "contains"]},
        },
        description="Custom identifier of the Profile.",
    )
    source_key: str = Field(
        ...,
        json_schema_extra={
            "prefilter": {"operators": ["eq", "in", "contains"]},
        },
    )
    info: ProfileInfo = Field(..., description="Object containing the Profile's info.")
    text_language: Optional[str] = Field(
        None, description="Code language of the Profile. type: string code ISO 639-1"
    )
    text: str = Field(..., description="Full text of the Profile..")
    archived_at: Optional[str] = Field(
        None,
        description=(
            "type: datetime ISO8601, Archive date of the Profile."
            " The value is null for unarchived Profiles."
        ),
    )
    updated_at: str = Field(
        ...,
        json_schema_extra={
            "cursor": ["updated_at"],
            "prefilter": {"operators": ["gte", "lte"]},
        },
        description="type: datetime ISO8601, Last update date of the Profile.",
    )
    created_at: str = Field(
        ...,
        json_schema_extra={
            "cursor": ["created_at"],
            "prefilter": {"operators": ["gte", "lte"]},
        },
        description="type: datetime ISO8601, Creation date of the Profile.",
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
        None, description="List of skills of the Profile."
    )
    languages: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of spoken languages of the profile"
    )
    certifications: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of certifications of the Profile."
    )
    courses: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of courses of the Profile."
    )
    tasks: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of tasks of the Profile."
    )
    interests: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of interests of the Profile."
    )
    tags: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of tags of the Profile."
    )
    metadatas: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of metadatas of the Profile."
    )
    labels: Optional[List[Label]] = Field(
        None, description="List of labels of the Profile."
    )
    payload: Dict[str, Any] = {}


# -------- Native event models (optional but handy) --------


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
