# hrtech_etl/cli.py
import json
import typer

from hrtech_etl.core.types import Resource, Cursor, CursorMode, PushMode
from hrtech_etl.core.pipeline import pull, push
from hrtech_etl.core.registry import get_connector_instance
from hrtech_etl.core.expressions import Condition  # si tu as un helper / dataclass Condition


app = typer.Typer()


def _parse_conditions(raw: str | None) -> list[Condition] | None:
    if not raw:
        return None
    data = json.loads(raw)
    # data = [{"field": "...", "op": "eq", "value": ...}, ...]
    conds: list[Condition] = []
    for item in data:
        conds.append(
            Condition(
                field=item["field"],
                op=item["op"],   # ou Operator(item["op"])
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
    where: str | None = typer.Option(None, help="JSON list of conditions"),
    having: str | None = typer.Option(None, help="JSON list of conditions"),
    formatter: str | None = typer.Option(None, help="dotted path to formatter"),
    batch_size: int = typer.Option(1000),
    dry_run: bool = typer.Option(False),
):
    res = Resource(resource)
    origin_conn = get_connector_instance(origin)
    target_conn = get_connector_instance(target)

    cur = Cursor(mode=CursorMode(cursor_mode), start=cursor_start, end=None)
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
    # tu peux passer events/resources via fichier ou stdin, à toi de voir
):
    # TODO: charger events/resources selon ton besoin
    ...


if __name__ == "__main__":
    app()
