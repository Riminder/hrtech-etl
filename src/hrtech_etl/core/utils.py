# hrtech_etl/core/utils.py
from functools import wraps
from typing import Any

from pydantic import BaseModel

from .types import CursorMode

def single_request(fn):
    """
    Ensure that an action executes exactly ONE underlying request
    via BaseRequests._request().
    """
    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        # reset counter before running
        self._request_count = 0

        result = fn(self, *args, **kwargs)

        if self._request_count != 1:
            raise AssertionError(
                f"{self.__class__.__name__}.{fn.__name__} performed "
                f"{self._request_count} requests instead of 1"
            )
        return result

    return wrapper


def get_cursor_value(obj: BaseModel, mode: CursorMode) -> Any:
    """
    Inspect a Pydantic model and return the value of the field
    tagged as the cursor for the given mode.
    """
    # This mapping ties CursorMode to our metadata string.
    target_tag = mode.value  # "updated_at", "created_at", or "id"

    # Pydantic v2: obj.model_fields
    # Pydantic v1: obj.__fields__
    fields_map = getattr(obj, "model_fields", None) or getattr(obj, "__fields__", {})

    for name, f in fields_map.items():
        # v2: json_schema_extra; v1: field_info.extra
        extra = getattr(f, "json_schema_extra", None)
        if not extra and hasattr(f, "field_info"):
            extra = getattr(f.field_info, "extra", None)

        if extra and extra.get("cursor") == target_tag:
            return getattr(obj, name)

    raise ValueError(
        f"No field with cursor={target_tag!r} on model {type(obj).__name__}"
    )
