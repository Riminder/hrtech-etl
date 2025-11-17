# src/hrtech_etl/formatters/base.py
from typing import Any, Dict, List, Protocol, TypeVar, Callable, Sequence, Optional

from pydantic import BaseModel


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
) -> Optional[Callable[[Any], Dict[str, Any]]]:
    """
    Build a simple mapping-based formatter.

    mapping: [{"from": "job_title", "to": "title"}, ...]

    Returns a callable that takes an origin object (Pydantic model, dataclass, etc.)
    and returns a dict where:
        data[dst] = getattr(origin_obj, src, None)
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
