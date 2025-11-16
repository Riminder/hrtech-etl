# hrtech_etl/core/pipeline.py
from typing import Any, Callable, List, Optional

from .types import CursorMode,Condition
from .connector import BaseConnector
from .utils import apply_postfilters, get_cursor_value

from pydantic import BaseModel
from importlib import import_module
from .registry import get_connector_instance

# core/pipeline.py
from .utils import apply_postfilters


class JobPullConfig(BaseModel):
    origin: str              # connector name, e.g. "warehouse_a"
    target: str              # connector name, e.g. "warehouse_b"
    cursor_mode: CursorMode
    cursor_start: Any = None
    where: List[Condition] = []  # prefilters
    having: List[Condition] = [] # NEW: postfilters on native
    formatter: Optional[str] = None    # dotted path, e.g. "hrtech_etl.formatters.a_to_b.format_job"
    formatter_id: Optional[str] | None = None
    limit: int = 1000
    dry_run: bool = False


def _load_callable(path: str) -> Callable[..., Any]:
    module_name, _, attr = path.rpartition(".")
    module = import_module(module_name)
    return getattr(module, attr)


def run_job_pull_from_config(cfg: JobPullConfig) -> Any:
    origin: BaseConnector = get_connector_instance(cfg.origin)
    target: BaseConnector = get_connector_instance(cfg.target)

    formatter = _load_callable(cfg.formatter) if cfg.formatter else None

    return pull_jobs(
        origin=origin,
        target=target,
        cursor_mode=cfg.cursor_mode,
        cursor_start=cfg.cursor_start,
        where=cfg.where,
        having=cfg.having,
        formatter=formatter,
        limit=cfg.limit,
        dry_run=cfg.dry_run,
    )


def pull_jobs(
    origin: BaseConnector,
    target: BaseConnector,
    cursor_mode: CursorMode,
    cursor_start: Any = None,   # value of the chosen cursor field
    where: list[Condition] | None = None,  # prefilters (Prefilter)
    having: list[Condition] | None = None, # NEW: postfilters on native
    formatter: Callable[[BaseModel], BaseModel] | None = None,
    limit: int = 1000,
    dry_run: bool = False,
) -> Any | None:
    """
    Returns the last cursor value (datetime or id),
    so you can store it and resume later.
    """
    if formatter is None:
        def default_format(native: Any) -> Any:
            unified = origin.to_unified_job(native)
            return target.from_unified_job(unified)
        active_format = default_format
    else:
        active_format = formatter

    cursor = cursor_start
    cursor_end = None

    while True:
        # 1) Read native jobs from origin (with prefilters translated to query)
        native_jobs, cursor = origin.read_jobs_batch(
            cursor_start=cursor,
            limit=limit,
            where=where,
            cursor_mode=cursor_mode,
        )
        if not native_jobs:
            break
        
        # 2) Apply postfilters IN MEMORY on native objects
        native_jobs = apply_postfilters(native_jobs, having)
        if not native_jobs:
            # no jobs left after postfiltering, but we still advance cursor
            if cursor is None:
                break
            cursor_end = cursor
            continue

        # 3) Compute cursor_end from the *last* native job in this batch
        #todo get_cursor_value should exist on the connector?
        #fixme
        cursor_end = origin.get_cursor_value(native_jobs[-1], cursor_mode)

        formatted = [active_format(j) for j in native_jobs]

        if not dry_run:
            target.write_jobs_batch(formatted)

        if cursor is None:
            break

    return cursor_end

