# hrtech_etl/core/pipeline.py
from importlib import import_module
from typing import Any, Callable, Iterable, List, Optional

from pydantic import BaseModel, Field

from hrtech_etl.formatters.base import JobFormatter, ProfileFormatter

from .connector import BaseConnector
from .models import UnifiedJobEvent, UnifiedProfileEvent
from .registry import get_connector_instance
from .types import Condition, Cursor, Formatter, PushMode, PushResult, Resource
from .utils import apply_postfilters, safe_format_resources

# -------- PULL RESOURCES: JOBS or PROFILES --------


def pull(
    resource: Resource,
    origin: BaseConnector,
    target: BaseConnector,
    cursor: Cursor,
    where: list[Condition] | None = None,  # prefilters (Prefilter)
    having: list[Condition] | None = None,  #  postfilters on native
    formatter: Formatter = None,
    batch_size: int = 1000,
    dry_run: bool = False,
) -> Cursor:
    """
    Incremental pull of jobs or profiles: origin → target.
    - `resource`: Resource.JOB or Resource.PROFILE
    - `where`: prefilters (pushed down to origin)
    - `having`: postfilters on native origin jobs or profiles (core)
    - `formatter`: explicit job or profile formatter; if None, use unified default
    """
    if not resource in (Resource.JOB, Resource.PROFILE):
        raise ValueError(f"pull() resource must be 'job' or 'profile', got: {resource}")

    current = cursor.start
    last_cursor: str | None = None

    while True:
        # 1) Read native resources from origin (with prefilters translated to query)
        native_resources, current = origin.read_resources_batch(
            resource=resource,
            where=where,
            cursor_start=current,
            cursor_mode=cursor.mode,
            batch_size=batch_size,
        )
        if not native_resources:
            break

        # 2) Apply postfilters IN MEMORY on native objects
        native_resources = apply_postfilters(native_resources, having)
        if not native_resources:
            # no resources left after postfiltering, but we still advance cursor
            if current is None:
                break
            last_cursor = current
            continue

        # 3) Compute last_cursor from the *last* native resource in this batch
        last_cursor = origin.get_cursor_from_native_resource(
            resource, native_resources[-1], cursor.mode
        )

        formatted_resources = safe_format_resources(
            resource, origin, target, formatter, native_resources
        )

        if not dry_run:
            target.write_resources_batch(resource, formatted_resources)

        if current is None:
            break

    return Cursor(mode=cursor.mode, start=cursor.start, end=last_cursor)


# -------- PUSH RESOURCES: JOBS or PROFILES --------


def push(
    resource: Resource,
    origin: BaseConnector,
    target: BaseConnector,
    mode: PushMode,
    events: Iterable[UnifiedJobEvent] | Iterable[UnifiedProfileEvent] | None = None,
    resources: Iterable[BaseModel] | None = None,
    having: list[Condition] | None = None,
    formatter: Formatter = None,
    batch_size: int = 1000,
    ignore_missing: bool = True,
    dry_run: bool = False,
) -> PushResult:
    """
    Push resources from origin → target.

    Two modes:
    - EVENTS: use `events` + origin.fetch_resources_by_events(...) to get native resources.
    - RESOURCES: use `resources` directly as native origin resources.

    Push mode:
    - `events`: unified JobEvent objects (created by connectors from raw payloads)
    - For each batch of events:
      - fetch native jobs from origin via `fetch_jobs_for_events`
      - apply HAVING conditions on native origin jobs
      - format (or origin-native -> UnifiedJob -> target-native)
      - write to target
    """
    if not resource in (Resource.JOB, Resource.PROFILE):
        raise ValueError(f"push() resource must be 'job' or 'profile', got: {resource}")

    total_events = 0
    total_fetched = 0
    total_pushed = 0
    skipped_missing = 0
    skipped_having = 0
    errors: list[str] = []

    if mode == PushMode.EVENTS:
        if events is None:
            raise ValueError("push(mode='events') requires `events`")
        events = list(events)
        total_events = len(events)

        for i in range(0, total_events, batch_size):
            batch_events = events[i : i + batch_size]

            try:
                native_resources = origin.fetch_resources_by_events(
                    resource, batch_events
                )
            except Exception as exc:
                errors.append(str(exc))
                continue

            total_fetched += len(native_resources)

            # Map resources by id using connector's get_resource_id()
            resources_by_id = {
                origin.get_resource_id(resource, r): r for r in native_resources
            }

            batch_to_push: list[BaseModel] = []

            for event in batch_events:
                resource_id = (
                    event.job_id if resource == Resource.JOB else event.profile_id
                )
                resource_by_event = resources_by_id.get(resource_id)

                if resource_by_event is None:
                    skipped_missing += 1
                    if not ignore_missing:
                        errors.append(
                            f"Missing {resource.value} for event {event.event_id} ({resource.value}_id={resource_id})"
                        )
                    continue

                # HAVING: postfilters on native origin job
                filtered = apply_postfilters([resource_by_event], having)
                if not filtered:
                    skipped_having += 1
                    continue

                batch_to_push.append(resource_by_event)

            if not batch_to_push:
                continue

            formatted_resources = safe_format_resources(
                resource, origin, target, formatter, batch_to_push
            )
            if not dry_run:
                target.write_resources_batch(resource, formatted_resources)

            total_pushed += len(batch_to_push)

    elif mode == PushMode.RESOURCES:
        if resources is None:
            raise ValueError("push(mode='resources') requires `resources`")
        resources = list(resources)
        total_fetched = len(resources)

        for i in range(0, total_fetched, batch_size):
            batch_resources = resources[i : i + batch_size]
            if batch_resources:
                # HAVING: postfilters on native origin resources
                filtered_resources = apply_postfilters(batch_resources, having)
                skipped_having += len(batch_resources) - len(filtered_resources)
                if filtered_resources:
                    formatted_resources = safe_format_resources(
                        resource, origin, target, formatter, filtered_resources
                    )
                    if not dry_run:
                        target.write_resources_batch(resource, formatted_resources)

                    total_pushed += len(filtered_resources)

    else:
        raise ValueError(f"Unknown PushMode: {mode}")

    return PushResult(
        total_events=total_events,
        total_resources_fetched=total_fetched,
        total_resources_pushed=total_pushed,
        skipped_missing=skipped_missing,
        skipped_having=skipped_having,
        errors=errors,
    )


# -------- CONFIG-DRIVEN JOB PULL --------


def _load_callable(path: str) -> Callable[..., Any]:
    module_name, _, attr = path.rpartition(".")
    module = import_module(module_name)
    return getattr(module, attr)


class ResourcePullConfig(BaseModel):
    resource: str
    origin: str
    target: str
    cursor: Cursor
    where: List[Condition] = Field(default_factory=list)
    having: List[Condition] = Field(default_factory=list)
    formatter: Optional[str] = None
    formatter_id: Optional[str] = None
    batch_size: int = 1000
    dry_run: bool = False


def run_resource_pull_from_config(cfg: ResourcePullConfig) -> Any:
    resource: Resource = Resource(cfg.resource)
    origin: BaseConnector = get_connector_instance(cfg.origin)
    target: BaseConnector = get_connector_instance(cfg.target)
    formatter = _load_callable(cfg.formatter) if cfg.formatter else None

    return pull(
        resource=resource,
        origin=origin,
        target=target,
        cursor=cfg.cursor,
        where=cfg.where,
        having=cfg.having,
        formatter=formatter,
        batch_size=cfg.batch_size,
        dry_run=cfg.dry_run,
    )


class ResourcePushConfig(BaseModel):
    resource: str
    origin: str
    target: str
    mode: str
    events: Optional[List[BaseModel]] = None
    resources: Optional[List[BaseModel]] = None
    having: List[Condition] = Field(default_factory=list)
    formatter: Optional[str] = None
    batch_size: int = 1000
    dry_run: bool = False


def run_resource_push_from_config(cfg: ResourcePushConfig) -> PushResult:
    resource: Resource = Resource(cfg.resource)
    origin: BaseConnector = get_connector_instance(cfg.origin)
    target: BaseConnector = get_connector_instance(cfg.target)
    mode: PushMode = PushMode(cfg.mode)
    formatter = _load_callable(cfg.formatter) if cfg.formatter else None

    return push(
        resource=resource,
        origin=origin,
        target=target,
        mode=mode,
        events=cfg.events,
        resources=cfg.resources,
        having=cfg.having,
        formatter=formatter,
        batch_size=cfg.batch_size,
        dry_run=cfg.dry_run,
    )
