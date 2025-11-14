# app/playground.py
from typing import Any, Optional, List, Dict

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from hrtech_etl.core.registry import list_connectors, get_connector_instance
from hrtech_etl.core.ui_schema import export_model_fields
from hrtech_etl.core.pipeline import pull_jobs, pull_profiles
from hrtech_etl.core.connector import BaseConnector
from hrtech_etl.core.types import Condition, Operator, CursorMode
from hrtech_etl.formatters.base import build_mapping_formatter

router = APIRouter()

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


def _parse_conditions_from_form(
    form: Dict[str, Any],
    prefix: str,
) -> List[Condition]:
    conditions: List[Condition] = []
    for i in range(MAX_FILTER_ROWS):
        field = form.get(f"{prefix}_field_{i}")
        op_str = form.get(f"{prefix}_op_{i}")
        value = form.get(f"{prefix}_value_{i}")
        if not field or not op_str or value is None or value == "":
            continue
        cond = Condition(field=field, op=Operator(op_str), value=value)
        conditions.append(cond)
    return conditions


def _condition_to_filter_fn(cond: Condition):
    op = cond.op
    field = cond.field
    raw_value = cond.value

    def _coerce(v: Any) -> Any:
        return v

    value = _coerce(raw_value)

    def fn(obj: Any) -> bool:
        attr = getattr(obj, field, None)
        if op == Operator.EQ:
            return attr == value
        if op == Operator.GT:
            return attr is not None and attr > value
        if op == Operator.LT:
            return attr is not None and attr < value
        if op == Operator.GTE:
            return attr is not None and attr >= value
        if op == Operator.LTE:
            return attr is not None and attr <= value
        if op == Operator.IN:
            values = [v.strip() for v in str(value).split(",")]
            return str(attr) in values
        if op == Operator.CONTAINS:
            return value in str(attr) if attr is not None else False
        return True

    return fn


@router.api_route("/playground", methods=["GET", "POST"], response_class=HTMLResponse)
async def playground(request: Request):
    connectors_meta = list(list_connectors().values())
    if not connectors_meta:
        return HTMLResponse("<h1>No connectors registered</h1>", status_code=500)

    form = await request.form() if request.method == "POST" else {}

    origin_name = form.get("origin") or connectors_meta[0].name
    target_name = form.get("target") or (
        connectors_meta[1].name if len(connectors_meta) > 1 else connectors_meta[0].name
    )
    resource = form.get("resource") or "job"

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
    origin_filter_fields = export_model_fields(origin_model, filterable_only=True)
    target_filter_fields = export_model_fields(target_model, filterable_only=True)

    result_summary: Optional[str] = None
    error_message: Optional[str] = None

    if request.method == "POST" and form.get("action") == "run":
        try:
            mapping = _parse_mapping_from_form(form)
            format_fn = build_mapping_formatter(mapping) if mapping else None

            pre_conditions = _parse_conditions_from_form(form, prefix="pre")
            post_conditions = _parse_conditions_from_form(form, prefix="post")
            post_filters = [_condition_to_filter_fn(c) for c in post_conditions] if post_conditions else None

            cursor_mode = CursorMode.UPDATED_AT

            if resource == "job":
                last_cursor = pull_jobs(
                    origin=origin_connector,
                    target=target_connector,
                    cursor_mode=cursor_mode,
                    where=pre_conditions or None,
                    format_fn=format_fn,
                    filters=post_filters,
                    batch_size=1000,
                    dry_run=False,
                )
            else:
                last_cursor = pull_profiles(
                    origin=origin_connector,
                    target=target_connector,
                    cursor_mode=cursor_mode,
                    where=pre_conditions or None,
                    format_fn=format_fn,
                    filters=post_filters,
                    batch_size=1000,
                    dry_run=False,
                )

            result_summary = f"ETL completed. Last cursor: {last_cursor!r}"
        except Exception as e:  # noqa: BLE001
            error_message = f"Error: {type(e).__name__}: {e}"

    html = _render_playground_html(
        connectors_meta=connectors_meta,
        origin_name=origin_name,
        target_name=target_name,
        resource=resource,
        origin_fields=origin_fields,
        target_fields=target_fields,
        origin_filter_fields=origin_filter_fields,
        target_filter_fields=target_filter_fields,
        result_summary=result_summary,
        error_message=error_message,
    )
    return HTMLResponse(html)


def _render_playground_html(
    connectors_meta,
    origin_name: str,
    target_name: str,
    resource: str,
    origin_fields: List[dict],
    target_fields: List[dict],
    origin_filter_fields: List[dict],
    target_filter_fields: List[dict],
    result_summary: Optional[str],
    error_message: Optional[str],
) -> str:
    def options_for_connectors(selected: str) -> str:
        parts = []
        for meta in connectors_meta:
            sel = "selected" if meta.name == selected else ""
            parts.append(
                f'<option value="{meta.name}" {sel}>{meta.label} ({meta.warehouse_type.value})</option>'
            )
        return "\n".join(parts)

    def options_for_fields(fields: List[dict]) -> str:
        parts = ['<option value="">--</option>']
        for f in fields:
            parts.append(f'<option value="{f["name"]}">{f["name"]} ({f["type"]})</option>')
        return "\n".join(parts)

    def options_for_ops() -> str:
        ops = [
            ("eq", "=="),
            ("gte", ">="),
            ("lte", "<="),
            ("gt", ">"),
            ("lt", "<"),
            ("in", "in (comma-separated)"),
            ("contains", "contains"),
        ]
        parts = ['<option value="">--</option>']
        for value, label in ops:
            parts.append(f'<option value="{value}">{label}</option>')
        return "\n".join(parts)

    mapping_rows_html = []
    for i in range(MAX_MAPPING_ROWS):
        mapping_rows_html.append(
            f"""
            <tr>
              <td><select name="mapping_from_{i}">{options_for_fields(origin_fields)}</select></td>
              <td><select name="mapping_to_{i}">{options_for_fields(target_fields)}</select></td>
            </tr>
            """
        )

    pre_filter_rows_html = []
    for i in range(MAX_FILTER_ROWS):
        pre_filter_rows_html.append(
            f"""
            <tr>
              <td><select name="pre_field_{i}">{options_for_fields(origin_filter_fields)}</select></td>
              <td><select name="pre_op_{i}">{options_for_ops()}</select></td>
              <td><input type="text" name="pre_value_{i}" /></td>
            </tr>
            """
        )

    post_filter_rows_html = []
    for i in range(MAX_FILTER_ROWS):
        post_filter_rows_html.append(
            f"""
            <tr>
              <td><select name="post_field_{i}">{options_for_fields(target_filter_fields)}</select></td>
              <td><select name="post_op_{i}">{options_for_ops()}</select></td>
              <td><input type="text" name="post_value_{i}" /></td>
            </tr>
            """
        )

    result_block = ""
    if result_summary:
        result_block = f'<div style="margin-top:1rem;padding:0.5rem;border:1px solid #0a0;"><strong>{result_summary}</strong></div>'
    if error_message:
        result_block += f'<div style="margin-top:1rem;padding:0.5rem;border:1px solid #a00;color:#a00;"><strong>{error_message}</strong></div>'

    html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>hrtech-etl Playground</title>
  <style>
    body {{ font-family: sans-serif; margin: 2rem; }}
    fieldset {{ margin-bottom: 1.5rem; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ccc; padding: 0.25rem 0.5rem; }}
    th {{ background-color: #f5f5f5; }}
  </style>
</head>
<body>
  <h1>hrtech-etl Playground</h1>

  <form method="post" action="/playground">
    <input type="hidden" name="action" value="run" />

    <fieldset>
      <legend>Connectors & Resource</legend>
      <label>Origin:
        <select name="origin">
          {options_for_connectors(origin_name)}
        </select>
      </label>
      &nbsp;&nbsp;
      <label>Target:
        <select name="target">
          {options_for_connectors(target_name)}
        </select>
      </label>
      &nbsp;&nbsp;
      <label>Resource:
        <select name="resource">
          <option value="job" {"selected" if resource == "job" else ""}>Job</option>
          <option value="profile" {"selected" if resource == "profile" else ""}>Profile</option>
        </select>
      </label>
    </fieldset>

    <fieldset>
      <legend>Mapping (Formatter)</legend>
      <p>Map origin fields to target fields. Empty rows are ignored.</p>
      <table>
        <thead>
          <tr><th>Origin field</th><th>Target field</th></tr>
        </thead>
        <tbody>
          {''.join(mapping_rows_html)}
        </tbody>
      </table>
    </fieldset>

    <fieldset>
      <legend>Pre-filters (origin WHERE)</legend>
      <p>These are applied as Conditions on origin objects (before hitting target).</p>
      <table>
        <thead>
          <tr><th>Field</th><th>Operator</th><th>Value</th></tr>
        </thead>
        <tbody>
          {''.join(pre_filter_rows_html)}
        </tbody>
      </table>
    </fieldset>

    <fieldset>
      <legend>Post-filters (after formatting)</legend>
      <p>These are applied in memory on mapped objects (after format_fn).</p>
      <table>
        <thead>
          <tr><th>Field</th><th>Operator</th><th>Value</th></tr>
        </thead>
        <tbody>
          {''.join(post_filter_rows_html)}
        </tbody>
      </table>
    </fieldset>

    <button type="submit">Run ETL</button>
  </form>

  {result_block}
</body>
</html>
"""
    return html
