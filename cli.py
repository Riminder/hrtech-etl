# hrtech_etl/cli.py
from __future__ import annotations  # 👈 safe for 3.8+ if you want to keep | syntax

import json
import typer

from hrtech_etl.core.types import (
    Resource,
    Cursor,
    CursorMode,
    PushMode,
    Condition,
    Operator,
)
from hrtech_etl.core.pipeline import pull, push
from hrtech_etl.core.registry import get_connector_instance


app = typer.Typer()


def _parse_conditions(raw: str | None) -> list[Condition] | None:
    """
    Expect JSON like:
      [
        {"field": "board_key", "op": "in", "value": ["b1", "b2"]},
        {"field": "name", "op": "contains", "value": "engineer"}
      ]
    """
    if not raw:
        return None
    data = json.loads(raw)

    conds: list[Condition] = []
    for item in data:
        conds.append(
            Condition(
                field=item["field"],
                op=Operator(item["op"]),  # 👈 map string -> Operator enum
                value=item["value"],
            )
        )
    return conds


@app.command()
def pull_cmd(
    resource: str = typer.Option("job", help="job|profile"),
    origin: str = typer.Option(..., help="origin connector name"),
    target: str = typer.Option(..., help="target connector name"),
    cursor_mode: str = typer.Option("updated_at"),
    cursor_start: str | None = typer.Option(None),
    cursor_sort_by: str = typer.Option("asc"),
    where: str | None = typer.Option(None, help="JSON list of conditions"),
    having: str | None = typer.Option(None, help="JSON list of conditions"),
    formatter: str | None = typer.Option(None, help="dotted path to formatter"),
    batch_size: int = typer.Option(1000),
    dry_run: bool = typer.Option(False),
):
    res = Resource(resource)
    origin_conn = get_connector_instance(origin)
    target_conn = get_connector_instance(target)

    cur = Cursor(
        mode=CursorMode(cursor_mode),
        start=cursor_start,
        end=None,
        sort_by=cursor_sort_by,
    )

    where_conds = _parse_conditions(where)
    having_conds = _parse_conditions(having)

    fmt_callable = None
    if formatter:
        module_name, _, attr = formatter.rpartition(".")
        mod = __import__(module_name, fromlist=[attr])
        fmt_callable = getattr(mod, attr)

    new_cursor = pull(
        resource=res,
        origin=origin_conn,
        target=target_conn,
        cursor=cur,
        where=where_conds,
        having=having_conds,
        formatter=fmt_callable,
        batch_size=batch_size,
        dry_run=dry_run,
    )
    typer.echo(new_cursor.model_dump_json())


@app.command()
def push_cmd(
    resource: str = typer.Option("job"),
    origin: str = typer.Option(...),
    target: str = typer.Option(...),
    mode: str = typer.Option("events"),   # events|resources
    # TODO: add options to pass events/resources (file path, stdin, etc.)
):
    # Not implemented yet – depends on how you want to feed events/resources.
    typer.echo("push_cmd not implemented yet.")



### Example usage:Simple pull: all jobs from warehouse_a → warehouse_a
### No WHERE, no HAVING, just incremental pull on updated_at

"""

python -m hrtech_etl.cli pull-cmd \
  --resource job \
  --origin warehouse_a \
  --target warehouse_a \
  --cursor-mode updated_at \
  --cursor-start "2024-01-01T00:00:00Z" \
  --cursor-sort-by asc \
  --batch-size 1000 \
  --dry-run True

"""

### Example usage: Pull with WHERE filters (IN + CONTAINS)


""""
python -m hrtech_etl.cli pull-cmd \
  --resource job \
  --origin warehouse_a \
  --target warehouse_a \
  --cursor-mode updated_at \
  --cursor-start "2024-01-01T00:00:00Z" \
  --cursor-sort-by asc \
  --where '[
    {"field": "board_key", "op": "in", "value": ["board-1", "board-2"]},
    {"field": "name",      "op": "contains", "value": "engineer"}
  ]' \
  --batch-size 1000 \
  --dry-run True
"""


### Example usage: Pull with HAVING filters (EQ on payload field)

"""
python -m hrtech_etl.cli pull-cmd \
    --resource job \
    --origin warehouse_a \
    --target warehouse_a \
    --cursor-mode updated_at \
    --cursor-start "2024-01-01T00:00:00Z"
    --cursor-sort-by asc \
    --where '[
        {"field": "board_key", "op": "in", "value": ["board-1", "board-2"]},
        {"field": "name",      "op": "contains", "value": "engineer"}
    ]' \    
    --having '[
        {"field": "payload.status", "op": "eq", "value": "closed"}
    ]' \
    --batch-size 1000 \
    --dry-run True

"""