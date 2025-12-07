# hrtech_etl/core/ui_schema.py
from typing import Any, Dict, List, Type

from pydantic import BaseModel


def export_model_fields(
    model_cls: Type[BaseModel],
    only_prefilterable: bool = False,
) -> List[Dict[str, Any]]:
    """
    Inspect a Pydantic model and expose its fields as a simple schema for the UI.

    Parameters
    ----------
    model_cls:
        The Pydantic model class to introspect
        (e.g. `UnifiedJob`, `WarehouseAJob`, `UnifiedProfile`, ...).

    only_prefilterable:
        - If False (default):
            Return **all** fields of the model, with any relevant metadata
            found in `json_schema_extra` (e.g. `cursor`, `prefilter`).
        - If True:
            Return **only** fields that are marked as prefilterable, i.e. fields
            having a `json_schema_extra["prefilter"]` block.

            This is typically used to build the list of fields that can be used
            in the "WHERE / Prefilter" section of the UI.

    Returned structure
    ------------------
    A list of JSON-serializable dictionaries, one per field, e.g.:

        [
          {
            "name": "created_at",
            "type": "str",
            "cursor": "created_at",
            "prefilter": {
              "operators": ["gte", "lte"]
            }
          },
          {
            "name": "board_key",
            "type": "str",
            "prefilter": {
              "operators": ["in"]
            }
          },
          {
            "name": "payload",
            "type": "dict"
          },
          ...
        ]

    Notes
    -----
    - The function is compatible with both Pydantic v1 and v2:
      it reads metadata from `field.json_schema_extra` (v2) or
      `field.field_info.extra` (v1), if present.

    - Only `cursor` and `prefilter` blocks are currently surfaced
      to the UI, but the function can be extended easily if you
      add more metadata in `json_schema_extra`.
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
