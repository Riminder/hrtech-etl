# hrtech_etl/core/pipeline.py
from typing import Any, Callable, List, Optional

from .types import FilterFn, CursorMode,Condition
from .connector import BaseConnector
from .utils import get_cursor_value

from pydantic import BaseModel
from importlib import import_module
from .registry import get_connector_instance


def _apply_filters(items: List[Any], filters: Optional[List[FilterFn]]) -> List[Any]:
    if not filters:
        return items
    return [x for x in items if all(f(x) for f in filters)]


def pull_jobs(
    origin: BaseConnector,
    target: BaseConnector,
    cursor_mode: CursorMode,
    format_fn: Optional[Callable[[Any], Any]] = None,
    filters: Optional[List[FilterFn]] = None,
    batch_size: int = 1000,
    dry_run: bool = False,
    start_cursor: Any = None,   # value of the chosen cursor field
) -> Any | None:
    """
    Returns the last cursor value (datetime or id),
    so you can store it and resume later.
    """
    if format_fn is None:
        def default_format(native: Any) -> Any:
            unified = origin.to_unified_job(native)
            return target.from_unified_job(unified)
        active_format = default_format
    else:
        active_format = format_fn

    cursor = start_cursor
    last_cursor_value = cursor

    while True:
        native_jobs, cursor = origin.read_jobs_batch(
            cursor=cursor,
            cursor_mode=cursor_mode,
            batch_size=batch_size,
        )
        if not native_jobs:
            break

        mapped = [active_format(j) for j in native_jobs]
        mapped = _apply_filters(mapped, filters)

        if not dry_run and mapped:
            target.write_jobs_batch(mapped)

        last_native = native_jobs[-1]
        last_cursor_value = get_cursor_value(last_native, cursor_mode)

        if cursor is None:
            break

    return last_cursor_value

class JobPullConfig(BaseModel):
    origin: str              # connector name, e.g. "warehouse_a"
    target: str              # connector name, e.g. "warehouse_b"
    cursor_mode: CursorMode
    where: List[Condition] = []
    formatter: Optional[str] = None    # dotted path, e.g. "hrtech_etl.formatters.a_to_b.format_job"
    batch_size: int = 1000
    dry_run: bool = False
    start_cursor: Any = None


def _load_callable(path: str) -> Callable[..., Any]:
    module_name, _, attr = path.rpartition(".")
    module = import_module(module_name)
    return getattr(module, attr)


def run_job_pull_from_config(cfg: JobPullConfig) -> Any:
    origin: BaseConnector = get_connector_instance(cfg.origin)
    target: BaseConnector = get_connector_instance(cfg.target)

    format_fn = _load_callable(cfg.formatter) if cfg.formatter else None

    return pull_jobs(
        origin=origin,
        target=target,
        cursor_mode=cfg.cursor_mode,
        where=cfg.where,
        format_fn=format_fn,
        batch_size=cfg.batch_size,
        dry_run=cfg.dry_run,
        start_cursor=cfg.start_cursor,
    )