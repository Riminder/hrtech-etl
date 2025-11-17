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
from hrtech_etl.core.types import Resource, PushMode
from hrtech_etl.core.pipeline import (
    pull,
    push,
    run_resource_pull_from_config,
    run_resource_push_from_config,
    ResourcePullConfig,
    ResourcePushConfig,
)

from hrtech_etl.formatters.base import FORMATTER_REGISTRY, build_mapping_formatter



router = APIRouter()

# ---------- CONNECTOR METADATA & SCHEMA ----------

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
    only_prefilterable: bool = False,
):
    """
    Expose native fields of a connector's job or profile model.

    Example:
      /api/schema/warehouse_a/job
      /api/schema/warehouse_a/job?only_prefilterable=true
    """
    try:
        connector = get_connector_instance(connector_name)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown connector")

    if resource == "job":
        model_cls = connector.job_native_cls
    else:
        model_cls = connector.profile_native_cls

    return export_model_fields(model_cls, only_prefilterable=only_prefilterable)


@router.get("/schema/unified/{resource}")
def unified_fields(
    resource: Literal["job", "profile"],
    only_prefilterable: bool = False,
):
    """
    Expose unified job/profile model fields.

    Example:
      /api/schema/unified/job
      /api/schema/unified/job?only_prefilterable=true
    """
    if resource == "job":
        model_cls = UnifiedJob
    else:
        model_cls = UnifiedProfile

    return export_model_fields(model_cls, only_prefilterable=only_prefilterable)


@router.post("/run/pull")
def run_pull(cfg: ResourcePullConfig):
    """
    Run a job pull based on a JSON config built in the UI.
    """
    cursor = run_resource_pull_from_config(cfg)
    return cursor.model_dump()

@router.post("/run/push")
def run_push(cfg: ResourcePushConfig):
    """
    Run a job push based on a JSON config built in the UI.
    """
    result = run_resource_push_from_config(cfg)
    return result.model_dump()


# ---------- FORMATTER BUILDING (MAPPING-BASED) ----------

class MappingItem(BaseModel):
    from_field: str = Field(alias="from")
    to_field: str = Field(alias="to")

    class Config:
        populate_by_name = True


class BuildFormatterRequest(BaseModel):
    resource: Literal["job", "profile"]
    origin: str
    target: str
    mapping: List[MappingItem]


class BuildFormatterResponse(BaseModel):
    formatter_id: str
    resource: str
    origin: str
    target: str
    mapping: List[MappingItem]


@router.post("/formatters/build", response_model=BuildFormatterResponse)
def build_formatter_route(req: BuildFormatterRequest):
    """
    Store a mapping spec and return a formatter_id.
    The actual Python formatter is built later with build_mapping_formatter()
    (using the mapping stored in FORMATTER_REGISTRY).
    """
    formatter_id = str(uuid4())

    # FORMATTER_REGISTRY is imported from hrtech_etl.formatters.base
    FORMATTER_REGISTRY[formatter_id] = {
        "resource": req.resource,
        "origin": req.origin,
        "target": req.target,
        "mapping": [
            {"from": item.from_field, "to": item.to_field}
            for item in req.mapping
        ],
    }

    return BuildFormatterResponse(
        formatter_id=formatter_id,
        resource=req.resource,
        origin=req.origin,
        target=req.target,
        mapping=req.mapping,
    )


@router.get("/formatters/{formatter_id}", response_model=BuildFormatterResponse)
def get_formatter_route(formatter_id: str):
    """
    Retrieve a stored formatter mapping by its formatter_id.
    """
    fmt_info = FORMATTER_REGISTRY.get(formatter_id)
    if not fmt_info:
        raise HTTPException(status_code=404, detail="Formatter not found")

    mapping = [
        MappingItem(from_field=item["from"], to_field=item["to"])
        for item in fmt_info["mapping"]
    ]

    return BuildFormatterResponse(
        formatter_id=formatter_id,
        resource=fmt_info["resource"],
        origin=fmt_info["origin"],
        target=fmt_info["target"],
        mapping=mapping,
    )

# ---------- RUN PULL / PUSH WITH formatter_id ----------

class RunPullWithFormatterRequest(BaseModel):
    formatter_id: str
    cfg: ResourcePullConfig


@router.post("/run/pull_with_formatter")
def run_pull_with_formatter(body: RunPullWithFormatterRequest):
    """
    Run a pull using a mapping-based formatter identified by formatter_id.

    Flow:
      - look up mapping in FORMATTER_REGISTRY
      - build a formatter with build_mapping_formatter(mapping)
      - call core.pull(...) with that formatter
    """
    fmt_info = FORMATTER_REGISTRY.get(body.formatter_id)
    if not fmt_info:
        raise HTTPException(status_code=404, detail="Formatter not found")

    cfg = body.cfg

    # sanity check – optional, but useful to avoid mismatches
    if fmt_info["resource"] != cfg.resource:
        raise HTTPException(
            status_code=400,
            detail=f"Formatter resource={fmt_info['resource']} "
                   f"does not match cfg.resource={cfg.resource}",
        )

    resource = Resource(cfg.resource)
    origin = get_connector_instance(cfg.origin)
    target = get_connector_instance(cfg.target)

    mapping = fmt_info["mapping"]  # list[{"from": "...", "to": "..."}]
    formatter = build_mapping_formatter(mapping)

    cursor = pull(
        resource=resource,
        origin=origin,
        target=target,
        cursor=cfg.cursor,
        where=cfg.where,
        having=cfg.having,
        formatter=formatter,
        batch_size=cfg.batch_size,
        dry_run=cfg.dry_run,
    )
    return cursor.model_dump()


class RunPushWithFormatterRequest(BaseModel):
    formatter_id: str
    cfg: ResourcePushConfig


@router.post("/run/push_with_formatter")
def run_push_with_formatter(body: RunPushWithFormatterRequest):
    """
    Run a push using a mapping-based formatter identified by formatter_id.

    Flow:
      - look up mapping in FORMATTER_REGISTRY
      - build a formatter with build_mapping_formatter(mapping)
      - call core.push(...) with that formatter
    """
    fmt_info = FORMATTER_REGISTRY.get(body.formatter_id)
    if not fmt_info:
        raise HTTPException(status_code=404, detail="Formatter not found")

    cfg = body.cfg

    if fmt_info["resource"] != cfg.resource:
        raise HTTPException(
            status_code=400,
            detail=f"Formatter resource={fmt_info['resource']} "
                   f"does not match cfg.resource={cfg.resource}",
        )

    resource = Resource(cfg.resource)
    origin = get_connector_instance(cfg.origin)
    target = get_connector_instance(cfg.target)
    mode = PushMode(cfg.mode)

    mapping = fmt_info["mapping"]  # list[{"from": "...", "to": "..."}]
    formatter = build_mapping_formatter(mapping)

    result = push(
        resource=resource,
        origin=origin,
        target=target,
        mode=mode,
        events=cfg.events,
        resources=cfg.resources,
        having=cfg.having,
        formatter=formatter,
        batch_size=cfg.batch_size,
        dry_run=cfg.dry_run,
    )
    return result.model_dump()
