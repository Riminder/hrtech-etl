# app/api.py
from typing import Literal, List, Dict
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from hrtech_etl.core.registry import (
    list_connectors,
    get_connector_instance,
)
from hrtech_etl.core.ui_schema import export_model_fields
from hrtech_etl.core.models import UnifiedJob, UnifiedProfile
from hrtech_etl.core.pipeline import JobPullConfig, run_job_pull_from_config
from hrtech_etl.formatters.base import MappingSpec, FORMATTER_REGISTRY

router = APIRouter()


@router.get("/connectors")
def connectors():
    """
    List all registered connectors.
    Frontend uses this to build origin/target dropdowns.
    """
    return [
        {
            "name": meta.name,
            "label": meta.label,
            "warehouse_type": meta.warehouse_type.value,
        }
        for meta in list_connectors().values()
    ]


@router.get("/schema/{connector_name}/{resource}")
def connector_fields(
    connector_name: str,
    resource: Literal["job", "profile"],
    filterable_only: bool = False,
):
    """
    Expose native fields of a connector's job or profile model.

    Example:
      /api/schema/warehouse_a/job
      /api/schema/warehouse_a/job?filterable_only=true
    """
    try:
        connector = get_connector_instance(connector_name)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown connector")

    if resource == "job":
        model_cls = connector.job_native_cls
    else:
        model_cls = connector.profile_native_cls

    return export_model_fields(model_cls, filterable_only=filterable_only)


@router.get("/schema/unified/{resource}")
def unified_fields(
    resource: Literal["job", "profile"],
    filterable_only: bool = False,
):
    """
    Expose unified job/profile model fields.

    Example:
      /api/schema/unified/job
      /api/schema/unified/job?filterable_only=true
    """
    if resource == "job":
        model_cls = UnifiedJob
    else:
        model_cls = UnifiedProfile

    return export_model_fields(model_cls, filterable_only=filterable_only)


@router.post("/run/job-pull")
def run_job_pull(cfg: JobPullConfig):
    """
    Run a job pull based on a JSON config built in the UI.
    """
    result = run_job_pull_from_config(cfg)
    return {"status": "ok", "last_cursor": result}


# ---------- FORMATTER BUILDING (MAPPING-BASED) ----------


class MappingItem(BaseModel):
    from_field: str = Field(alias="from")
    to_field: str = Field(alias="to")

    class Config:
        populate_by_name = True


class BuildFormatterRequest(BaseModel):
    mapping: List[MappingItem]


class BuildFormatterResponse(BaseModel):
    formatter_id: str
    mapping: List[MappingItem]


@router.post("/formatters/build", response_model=BuildFormatterResponse)
def build_formatter_route(req: BuildFormatterRequest):
    """
    Store a mapping spec and return a formatter_id.
    The actual Python formatter is built later with build_mapping_formatter().
    """
    formatter_id = str(uuid4())

    FORMATTER_REGISTRY[formatter_id] = [
        {"from": item.from_field, "to": item.to_field} for item in req.mapping
    ]

    return BuildFormatterResponse(
        formatter_id=formatter_id,
        mapping=req.mapping,
    )
