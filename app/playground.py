# app/playground.py
from typing import Any, Optional, List, Dict, Type
import json

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from hrtech_etl.core.connector import BaseConnector
from hrtech_etl.core.registry import list_connectors, get_connector_instance
from hrtech_etl.core.ui_schema import export_model_fields
from hrtech_etl.core.types import (
    Condition,
    Operator,
    Cursor,
    CursorMode,
    Resource,
    PushMode,
)
from hrtech_etl.core.expressions import Prefilter
from hrtech_etl.core.pipeline import pull, push
from hrtech_etl.core.models import UnifiedJobEvent, UnifiedProfileEvent
from hrtech_etl.formatters.base import build_mapping_formatter

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

MAX_MAPPING_ROWS = 5
MAX_FILTER_ROWS = 5


def _parse_mapping_from_form(form: Dict[str, Any]) -> List[Dict[str, str]]:
    mapping: List[Dict[str, str]] = []
    for i in range(MAX_MAPPING_ROWS):
        src = form.get(f"mapping_from_{i}")
        dst = form.get(f"mapping_to_{i}")
        if src and dst:
            mapping.append({"from": src, "to": dst})
    return mapping


def _parse_prefilter_conditions(
    form: Dict[str, Any],
    model_cls: Type[BaseModel],
) -> List[Condition]:
    conditions: List[Condition] = []

    for i in range(MAX_FILTER_ROWS):
        field_name = form.get(f"pre_field_{i}")
        op_str = form.get(f"pre_op_{i}")
        value = form.get(f"pre_value_{i}")

        if not field_name or not op_str or value is None or value == "":
            continue

        builder = Prefilter(model_cls, field_name)

        if op_str == "eq":
            cond = builder.eq(value)
        elif op_str == "gt":
            cond = builder.gt(value)
        elif op_str == "gte":
            cond = builder.gte(value)
        elif op_str == "lt":
            cond = builder.lt(value)
        elif op_str == "lte":
            cond = builder.lte(value)
        elif op_str == "contains":
            cond = builder.contains(value)
        elif op_str == "in":
            values = [v.strip() for v in str(value).split(",")]
            cond = builder.in_(values)
        else:
            raise ValueError(f"Unknown operator {op_str!r}")

        conditions.append(cond)

    return conditions


def _parse_postfilter_conditions(form: Dict[str, Any]) -> List[Condition]:
    conditions: List[Condition] = []

    for i in range(MAX_FILTER_ROWS):
        field_name = form.get(f"post_field_{i}")
        op_str = form.get(f"post_op_{i}")
        value = form.get(f"post_value_{i}")

        if not field_name or not op_str or value is None or value == "":
            continue

        cond = Condition(field=field_name, op=Operator(op_str), value=value)
        conditions.append(cond)

    return conditions


def _parse_resources_json(
    form: Dict[str, Any],
    model_cls: Type[BaseModel],
) -> List[BaseModel]:
    """
    Parse a JSON array from 'resources_json' into a list of native Pydantic models.
    Used for push(mode=RESOURCES) in the playground.
    """
    raw = form.get("resources_json")
    if not raw:
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in resources_json: {exc}") from exc

    if not isinstance(data, list):
        raise ValueError("resources_json must be a JSON array of objects")

    resources: List[BaseModel] = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("Each resource must be a JSON object")
        if hasattr(model_cls, "model_validate"):  # pydantic v2
            resources.append(model_cls.model_validate(item))  # type: ignore[attr-defined]
        else:  # pydantic v1
            resources.append(model_cls.parse_obj(item))  # type: ignore[attr-defined]
    return resources


def _parse_events_json(
    form: Dict[str, Any],
    resource: Resource,
) -> List[BaseModel]:
    """
    Parse a JSON array from 'events_json' into a list of UnifiedJobEvent or UnifiedProfileEvent.
    Used for push(mode=EVENTS) in the playground.
    """
    raw = form.get("events_json")
    if not raw:
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in events_json: {exc}") from exc

    if not isinstance(data, list):
        raise ValueError("events_json must be a JSON array of objects")

    events: List[BaseModel] = []
    model_cls: Type[BaseModel]
    if resource == Resource.JOB:
        model_cls = UnifiedJobEvent
    else:
        model_cls = UnifiedProfileEvent

    for item in data:
        if not isinstance(item, dict):
            raise ValueError("Each event must be a JSON object")
        if hasattr(model_cls, "model_validate"):  # pydantic v2
            events.append(model_cls.model_validate(item))  # type: ignore[attr-defined]
        else:
            events.append(model_cls.parse_obj(item))  # type: ignore[attr-defined]
    return events


def _build_context(
    request: Request,
    operation: str,
    push_mode: str,
    origin_name: str,
    target_name: str,
    resource: str,
    cursor_mode: Optional[str],
    cursor_start: Optional[str],
    cursor_end: Optional[str],
    origin_fields: List[dict],
    target_fields: List[dict],
    origin_prefilter_fields: List[dict],
    origin_postfilter_fields: List[dict],
    resources_json: str,
    events_json: str,
    result_summary: Optional[str],
    error_message: Optional[str],
) -> Dict[str, Any]:
    return {
        "request": request,
        "connectors_meta": list(list_connectors().values()),
        "operation": operation,
        "push_mode": push_mode,
        "origin_name": origin_name,
        "target_name": target_name,
        "resource": resource,
        "cursor_mode": cursor_mode,
        "cursor_start": cursor_start,
        "cursor_end": cursor_end,
        "origin_fields": origin_fields,
        "target_fields": target_fields,
        "origin_prefilter_fields": origin_prefilter_fields,
        "origin_postfilter_fields": origin_postfilter_fields,
        "resources_json": resources_json,
        "events_json": events_json,
        "result_summary": result_summary,
        "error_message": error_message,
        "MAX_MAPPING_ROWS": MAX_MAPPING_ROWS,
        "MAX_FILTER_ROWS": MAX_FILTER_ROWS,
    }


@router.api_route("/playground", methods=["GET", "POST"], response_class=HTMLResponse)
async def playground(request: Request):
    """
    hrtech-etl Playground UI.

    - Operation: pull | push
    - push.mode: RESOURCES | EVENTS
    - Select origin/target connectors
    - Select resource: job | profile
    - Build field mappings (formatter)
    - Define pre-filters (Prefilter) for pull
    - Define post-filters (in-memory HAVING) for both pull and push
    - For push/RESOURCES: paste native resources as JSON.
    - For push/EVENTS: paste UnifiedJobEvent / UnifiedProfileEvent as JSON.
    """
    connectors_meta = list(list_connectors().values())
    if not connectors_meta:
        return HTMLResponse("<h1>No connectors registered</h1>", status_code=500)

    form = await request.form() if request.method == "POST" else {}

    operation = form.get("operation") or "pull"  # "pull" or "push"
    push_mode = form.get("push_mode") or "resources"  # "resources" or "events"

    origin_name = form.get("origin") or connectors_meta[0].name
    target_name = form.get("target") or (
        connectors_meta[1].name if len(connectors_meta) > 1 else connectors_meta[0].name
    )

    resource_str = form.get("resource") or "job"
    try:
        resource_enum = Resource(resource_str)
    except ValueError:
        resource_enum = Resource.JOB

    cursor_mode_str = form.get("cursor_mode") or CursorMode.UPDATED_AT.value
    cursor_mode_enum = CursorMode(cursor_mode_str)
    cursor_start = form.get("cursor_start") or None

    cursor = Cursor(
        mode=cursor_mode_enum,
        start=cursor_start,
        end=None,
    )

    resources_json = form.get("resources_json") or ""
    events_json = form.get("events_json") or ""

    try:
        origin_connector: BaseConnector = get_connector_instance(origin_name)
        target_connector: BaseConnector = get_connector_instance(target_name)
    except KeyError:
        return HTMLResponse("<h1>Unknown connector selected</h1>", status_code=400)

    # choose native model classes for the resource
    if resource_enum == Resource.JOB:
        origin_model = origin_connector.job_native_cls
        target_model = target_connector.job_native_cls
    else:
        origin_model = origin_connector.profile_native_cls
        target_model = target_connector.profile_native_cls

    # full fields (for mapping + postfilters)
    origin_fields = export_model_fields(origin_model, only_prefilterable=False)
    target_fields = export_model_fields(target_model, only_prefilterable=False)
    # prefilterable fields (Prefilter)
    origin_prefilter_fields = export_model_fields(origin_model, only_prefilterable=True)
    # postfilters can use all fields
    origin_postfilter_fields = origin_fields

    result_summary: Optional[str] = None
    error_message: Optional[str] = None

    if request.method == "POST" and form.get("action") == "run":
        try:
            mapping = _parse_mapping_from_form(form)
            formatter = build_mapping_formatter(mapping) if mapping else None

            pre_conditions = _parse_prefilter_conditions(form, origin_model)
            post_conditions = _parse_postfilter_conditions(form)

            if operation == "pull":
                cursor = pull(
                    resource=resource_enum,
                    origin=origin_connector,
                    target=target_connector,
                    cursor=cursor,
                    where=pre_conditions or None,
                    having=post_conditions or None,
                    formatter=formatter,
                    batch_size=1000,
                    dry_run=False,
                )
                result_summary = f"[PULL] ETL completed. Last cursor: {cursor.end!r}"

            elif operation == "push":
                if push_mode == "resources":
                    native_resources = _parse_resources_json(form, origin_model)

                    if not native_resources:
                        raise ValueError(
                            "No resources provided for push (RESOURCES mode). "
                            "Fill the 'Resources JSON' textarea with a JSON array."
                        )

                    result = push(
                        resource=resource_enum,
                        origin=origin_connector,
                        target=target_connector,
                        mode=PushMode.RESOURCES,
                        events=None,
                        resources=native_resources,
                        having=post_conditions or None,
                        formatter=formatter,
                        batch_size=1000,
                        dry_run=False,
                    )
                    result_summary = (
                        f"[PUSH/RESOURCES] total_fetched={result.total_resources_fetched}, "
                        f"pushed={result.total_resources_pushed}, "
                        f"skipped_missing={result.skipped_missing}, "
                        f"skipped_having={result.skipped_having}"
                    )

                elif push_mode == "events":
                    events = _parse_events_json(form, resource_enum)

                    if not events:
                        raise ValueError(
                            "No events provided for push (EVENTS mode). "
                            "Fill the 'Events JSON' textarea with a JSON array."
                        )

                    result = push(
                        resource=resource_enum,
                        origin=origin_connector,
                        target=target_connector,
                        mode=PushMode.EVENTS,
                        events=events,
                        resources=None,
                        having=post_conditions or None,
                        formatter=formatter,
                        batch_size=1000,
                        dry_run=False,
                    )
                    result_summary = (
                        f"[PUSH/EVENTS] total_events={result.total_events}, "
                        f"resources_fetched={result.total_resources_fetched}, "
                        f"pushed={result.total_resources_pushed}, "
                        f"skipped_missing={result.skipped_missing}, "
                        f"skipped_having={result.skipped_having}"
                    )
                else:
                    raise ValueError(f"Unknown push_mode {push_mode!r}")

            else:
                raise ValueError(f"Unknown operation {operation!r}")

        except Exception as e:  # noqa: BLE001
            error_message = f"Error: {type(e).__name__}: {e}"

    context = _build_context(
        request=request,
        operation=operation,
        push_mode=push_mode,
        origin_name=origin_name,
        target_name=target_name,
        resource=resource_enum.value,
        cursor_mode=cursor.mode.value if cursor else None,
        cursor_start=cursor.start if cursor else None,
        cursor_end=cursor.end if cursor else None,
        origin_fields=origin_fields,
        target_fields=target_fields,
        origin_prefilter_fields=origin_prefilter_fields,
        origin_postfilter_fields=origin_postfilter_fields,
        resources_json=resources_json,
        events_json=events_json,
        result_summary=result_summary,
        error_message=error_message,
    )
    return templates.TemplateResponse("playground.html", context)
