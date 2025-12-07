# src/hrtech_etl/formatters/base.py
from typing import Any, Callable, Dict, List, Optional, Protocol, Sequence, TypeVar

from pydantic import BaseModel

from hrtech_etl.core.types import Formatter

JIn = TypeVar("JIn", bound=BaseModel)
JOut = TypeVar("JOut")
PIn = TypeVar("PIn", bound=BaseModel)
POut = TypeVar("POut")


# Global registry used by the API layer to store formatter specs:
# {
#   formatter_id: {
#     "resource": "job" | "profile",
#     "origin": "warehouse_a",
#     "target": "warehouse_b",
#     "mapping": [{"from": "...", "to": "..."}, ...],
#   },
# }
FORMATTER_REGISTRY: Dict[str, Dict] = {}


class JobFormatter(Protocol[JIn, JOut]):
    def __call__(self, job: JIn) -> JOut:
        return NotImplemented


class ProfileFormatter(Protocol[PIn, POut]):
    def __call__(self, profile: PIn) -> POut:
        return NotImplemented


MappingSpec = Dict[str, str]  # {"from": "job_title", "to": "title"}


def build_mapping_formatter(
    mapping: Sequence[MappingSpec],
) -> Optional[Formatter]:
    """
    Build a simple mapping-based formatter.

    Parameters
    ----------
    mapping:
        Sequence of {"from": src_field, "to": dst_field} dicts.
        Example:
            [{"from": "job_id", "to": "id"},
             {"from": "title",  "to": "name"}]

    Returns
    -------
    formatter:
        A callable suitable for use as a `Formatter` in the pipeline:
            - Takes an origin object (Pydantic model, dataclass, etc.)
            - Returns a `dict` where each `to` field is filled from
              `getattr(origin_obj, from, None)`.

        This dict is then wrapped into the *target* native model by
        `safe_format_resources(...)`.
    """
    if not mapping:
        return None

    # normalize once
    normalized: List[MappingSpec] = [
        {"from": m["from"], "to": m["to"]} for m in mapping
    ]

    def formatter(origin_obj: Any) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        for item in normalized:
            src = item["from"]
            dst = item["to"]
            data[dst] = getattr(origin_obj, src, None)
        return data

    return formatter
