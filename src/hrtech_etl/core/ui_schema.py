# hrtech_etl/core/ui_schema.py
from typing import Any, Dict, List, Type

from pydantic import BaseModel


def export_model_fields(
    model_cls: Type[BaseModel],
    only_prefilterable: bool = False,
) -> List[Dict[str, Any]]:
    """
    Return metadata about a Pydantic model's fields for UI use.

    If filterable_only is False:
        - returns ALL fields with any extra metadata (cursor/filter/…)
    If filterable_only is True:
        - returns ONLY fields that have filter.eligible = True in json_schema_extra

    Example output (filterable_only=False):
    [
      {
        "name": "job_id",
        "type": "str",
        "cursor": "id",
        "filter": {
          "eligible": true,
          "operators": ["eq", "in"]
        }
      },
      ...
    ]
    """
    fields_map = getattr(model_cls, "model_fields", None) or getattr(
        model_cls, "__fields__", {}
    )

    result: List[Dict[str, Any]] = []

    for name, f in fields_map.items():
        # Figure out python type name
        annotation = getattr(f, "annotation", Any)
        py_type = getattr(annotation, "__name__", str(annotation))

        # pydantic v1/v2 compatibility for extra metadata
        extra = getattr(f, "json_schema_extra", None)
        if not extra and hasattr(f, "field_info"):
            extra = getattr(f.field_info, "extra", None)
        extra = extra or {}

        prefilter_meta = extra.get("prefilter")

        # if we only want prefilterable fields, keep those that have a prefilter block
        if only_prefilterable and not prefilter_meta:
            continue

        field_info: Dict[str, Any] = {
            "name": name,
            "type": py_type,
        }

        if "cursor" in extra:
            field_info["cursor"] = extra["cursor"]

        if prefilter_meta:
            field_info["prefilter"] = prefilter_meta  # no 'eligible' anymore

        result.append(field_info)

    return result
