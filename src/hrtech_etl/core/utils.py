# hrtech_etl/core/utils.py
from functools import wraps
from typing import Any

from pydantic import BaseModel

from .types import CursorMode, Condition, Operator

from typing import Any, Iterable, List

from .connector import BaseConnector
from hrtech_etl.formatters.base import JobFormatter, ProfileFormatter


def safe_format_jobs(
    origin: BaseConnector,
    target: BaseConnector,
    formatter: JobFormatter | None,
    native_jobs: List[BaseModel],
) -> List[BaseModel]:
    """
    Use explicit formatter if provided, otherwise:
    origin-native → UnifiedJob → target-native.
    """
    if formatter is not None:
        return [formatter(job) for job in native_jobs]

    unified_jobs = [origin.to_unified_job(job) for job in native_jobs]
    return [target.from_unified_job(uj) for uj in unified_jobs]


def safe_format_profiles(
    origin: BaseConnector,
    target: BaseConnector,
    formatter: ProfileFormatter | None,
    native_profiles: List[BaseModel],
) -> List[BaseModel]:
    if formatter is not None:
        return [formatter(p) for p in native_profiles]

    unified_profiles = [origin.to_unified_profile(p) for p in native_profiles]
    return [target.from_unified_profile(up) for up in unified_profiles]


def _match_condition(value: Any, cond: Condition) -> bool:
    op = cond.op
    target = cond.value

    if op == Operator.EQ:
        return value == target
    if op == Operator.GT:
        return value is not None and value > target
    if op == Operator.GTE:
        return value is not None and value >= target
    if op == Operator.LT:
        return value is not None and value < target
    if op == Operator.LTE:
        return value is not None and value <= target
    if op == Operator.IN:
        return value in (target or [])
    if op == Operator.CONTAINS:
        return value is not None and str(target) in str(value)
    #TODO extend with more ops (startswith, endswith, regex, etc.)
    return True


def apply_postfilters(
    items: Iterable[BaseModel],
    conditions: list[Condition] | None,
) -> list[BaseModel]:
    """
    Apply postfilters in memory on native objects.

    - Works on ANY field of the native model
    - Allows ALL operators defined in Operator, independent of `prefilter` metadata
    """
    if not conditions:
        return list(items)

    def matches(obj: BaseModel) -> bool:
        for cond in conditions:
            attr = getattr(obj, cond.field, None)
            if not _match_condition(attr, cond):
                return False
        return True

    return [obj for obj in items if matches(obj)]


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
