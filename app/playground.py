# app/playground.py
from typing import Any, Optional, List, Dict, Type

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from hrtech_etl.core.connector import BaseConnector
from hrtech_etl.core.registry import list_connectors, get_connector_instance
from hrtech_etl.core.ui_schema import export_model_fields
from hrtech_etl.core.types import Condition, Operator, CursorMode
from hrtech_etl.core.expressions import Prefilter
from hrtech_etl.core.pipeline import pull_jobs, pull_profiles
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

def _build_context(
    request: Request,
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
    result_summary: Optional[str],
    error_message: Optional[str],
) -> Dict[str, Any]:
    return {
        "request": request,
        "connectors_meta": list_connectors().values(),
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
        "result_summary": result_summary,
        "error_message": error_message,
        "MAX_MAPPING_ROWS": MAX_MAPPING_ROWS,
        "MAX_FILTER_ROWS": MAX_FILTER_ROWS,
    }



@router.api_route("/playground", methods=["GET", "POST"], response_class=HTMLResponse)
async def playground(request: Request):
    """
    hrtech-etl Playground UI.
    Allows you to select origin/target connectors, define field mappings (formatter),
    pre-filters (prefilter Conditions), and post-filters (in-memory Conditions).
    Then runs a pull_jobs or pull_profiles ETL based on your selections.
    Async function
    """
    connectors_meta = list(list_connectors().values())
    if not connectors_meta:
        return HTMLResponse("<h1>No connectors registered</h1>", status_code=500)

    form = await request.form() if request.method == "POST" else {}

    origin_name = form.get("origin") or connectors_meta[0].name
    target_name = form.get("target") or (
        connectors_meta[1].name if len(connectors_meta) > 1 else connectors_meta[0].name
    )
    resource = form.get("resource") or "job"
    cursor_mode = CursorMode(form.get("cursor_mode") or CursorMode.UPDATED_AT)
    cursor_start = form.get("cursor_start") or None
    cursor_end = None

    try:
        origin_connector: BaseConnector = get_connector_instance(origin_name)
        target_connector: BaseConnector = get_connector_instance(target_name)
    except KeyError:
        return HTMLResponse("<h1>Unknown connector selected</h1>", status_code=400)

    if resource == "job":
        origin_model = origin_connector.job_native_cls
        target_model = target_connector.job_native_cls
    else:
        origin_model = origin_connector.profile_native_cls
        target_model = target_connector.profile_native_cls

    origin_fields = export_model_fields(origin_model, filterable_only=False)
    target_fields = export_model_fields(target_model, filterable_only=False)
    origin_prefilter_fields = export_model_fields(origin_model, filterable_only=True)
    origin_postfilter_fields = origin_fields

    result_summary: Optional[str] = None
    error_message: Optional[str] = None

    if request.method == "POST" and form.get("action") == "run":
        try:
            mapping = _parse_mapping_from_form(form)
            formatter = build_mapping_formatter(mapping) if mapping else None

            pre_conditions = _parse_prefilter_conditions(form, origin_model)
            post_conditions = _parse_postfilter_conditions(form)

            if resource == "job":
                last_cursor = pull_jobs(
                    origin=origin_connector,
                    target=target_connector,
                    cursor_mode=cursor_mode,
                    cursor_start=cursor_start,
                    where=pre_conditions or None,
                    having=post_conditions or None,
                    formatter=formatter or None,
                    limit=1000,
                    dry_run=False,
                )
            else:
                last_cursor = pull_profiles(
                    origin=origin_connector,
                    target=target_connector,
                    cursor_mode=cursor_mode,
                    cursor_start=cursor_start,
                    where=pre_conditions or None,
                    having=post_conditions or None,
                    formatter=formatter or None,
                    limit=1000,
                    dry_run=False,
                )

            result_summary = f"ETL completed. Last cursor: {cursor_end!r}"
        except Exception as e:  # noqa: BLE001
            error_message = f"Error: {type(e).__name__}: {e}"

    cursor_end = str(last_cursor) if last_cursor is not None else None

    context = _build_context(
        request=request,
        origin_name=origin_name,
        target_name=target_name,
        resource=resource,
        cursor_mode=cursor_mode,
        cursor_start=cursor_start,
        cursor_end=cursor_end,
        origin_fields=origin_fields,
        target_fields=target_fields,
        origin_prefilter_fields=origin_prefilter_fields,
        origin_postfilter_fields=origin_postfilter_fields,
        result_summary=result_summary,
        error_message=error_message,
    )
    return templates.TemplateResponse("playground.html", context)
