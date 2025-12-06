# hrtech_etl/core/models.py
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from .types import BoolJoin, Cursor, CursorMode, JobEventType, ProfileEventType

from __future__ import annotations

#TOD limit prefilter to eq or in for keys

# --- UNIFIED RESOURCES EVENTS ---

class UnifiedJobEvent(BaseModel):
    event_id: str
    job_id: str
    type: JobEventType
    occurred_at: Optional[datetime] = None
    payload: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}


class UnifiedProfileEvent(BaseModel):
    event_id: str
    profile_id: str
    type: ProfileEventType
    occurred_at: Optional[datetime] = None
    payload: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}


# --- UNIFIED RESOURCES UTILS ---

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


# --- UNIFIED JOB UTILS ---


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


# --- UNIFIED JOBS ---

class UnifiedJob(BaseModel):
    id:Optional[str] = Field(
        description="Unique identifier of the Job."
    )
    origin: str # e.g., 'warehouse_a'
    payload: Optional[Dict[str, Any]] = None
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
                "query_field": "board_keys",   # query field name
                "formatter": "string_array",    # which formatter to use from .utils.formatters csv, array, string_array
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
                "group_join": BoolJoin.AND,      # => (name) OR (skills
                # "field_join": BoolJoin.OR,        # => name1 OR name2 OR name3...
            }
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
            "group_join": BoolJoin.AND,      # => (text) AND (skills...)
            # "field_join": BoolJoin.OR,        # => text1 OR text2 OR text3...
            },
        }
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
            "query_field": "tags",   # query field name
            "formatter": "string_array",    # which formatter to use from .utils.formatters: csv, array, string_array
            },
        }
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
    


# --- UNIFIED PROFILE UTILS ---

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
    title: Optional[str] = Field(None, description="Title of the Experience.")
    company: Optional[str] = Field(None, description="Company name of the Experience.")
    date_start: Optional[str] = Field(
        None, description="Start date of the experience. type: ('datetime ISO 8601')"
    )
    date_end: Optional[str] = Field(
        None, description="End date of the experience. type: ('datetime ISO 8601')"
    )
    location: Optional[Location] = Field(
        None, description="Location object of the Experience."
    )
    description: Optional[str] = Field(
        None, description="Description of the Experience."
    )
    skills: Optional[List[Skill]] = Field(
        None, description="List of skills of the Experience."
    )
    languages: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of spoken languages of the profile"
    )
    tasks: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of tasks of the Experience."
    )
    certifications: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of certifications of the Experience."
    )
    courses: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of courses of the Experience."
    )
    interests: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of interests of the Experience."
    )
    logo: Optional[str] = Field(None, description="Logo of the Company.")


class Education(BaseModel):
    key: Optional[str] = Field(None, description="Identification key of the Education.")
    title: Optional[str] = Field(None, description="Title of the Education.")
    school: Optional[str] = Field(None, description="School name of the Education.")
    date_start: Optional[str] = Field(
        None, description="Start date of the Education. type: ('datetime ISO 8601')"
    )
    date_end: Optional[str] = Field(
        None, description="End date of the Education. type: ('datetime ISO 8601')"
    )
    location: Optional[Location] = Field(
        None, description="Location object of the Education."
    )
    description: Optional[str] = Field(
        None, description="Description of the Education."
    )
    skills: Optional[List[Skill]] = Field(
        None, description="List of skills of the Education."
    )
    languages: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of spoken languages of the profile"
    )
    tasks: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of tasks of the Education."
    )
    certifications: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of certifications of the Education."
    )
    courses: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of courses of the Education."
    )
    interests: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of interests of the Experience."
    )
    logo: Optional[str] = Field(None, description="Logo of the School.")


class Attachment(BaseModel):
    created_at: Optional[str]
    updated_at: Optional[str]
    original_file_name: Optional[str]
    extension: Optional[str]
    type: Optional[str]
    alt: Optional[str]
    file_size: Optional[str]
    file_name: Optional[str]
    public_url: Optional[str]


# --- UNIFIED PROFILE ---

class UnifiedProfile(BaseModel): 
    id:Optional[str] = Field(
        description="Unique identifier of the Job."
    )
    origin: str # e.g., 'warehouse_a'
    payload: Optional[Dict[str, Any]] = None
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
            "query_field": "source_keys",   # query field name
            "formatter": "string_array",    # which formatter to use from .utils.formatters csv, array, string_array
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
            "group_join": BoolJoin.AND,      # => (text) AND (skills...)
            # "field_join": BoolJoin.OR,        # => text1 OR text2 OR text3...
            },
        }
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
        None, description="List of skills of the Profile.",
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
            "query_field": "tags",   # query field name
            "formatter": "array",    # which formatter to use from .utils.formatters
            },
        }
    )
    metadatas: Optional[List[GeneralEntitySchema]] = Field(
        None, description="List of metadatas of the Profile."
    )
    labels: Optional[List[Label]] = Field(
        None, description="List of labels of the Profile."
    )


