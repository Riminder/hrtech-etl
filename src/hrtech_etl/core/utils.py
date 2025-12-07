# hrtech_etl/core/utils.py
from functools import wraps
from typing import Any, Dict, Iterable, List, Optional, Type, Union, Callable

import json

from pydantic import BaseModel

from .connector import BaseConnector
from .types import Condition, Cursor, CursorMode, Formatter, Operator, Resource,  BoolJoin


def safe_format_resources(
    resource: Resource,
    origin: BaseConnector,
    target: BaseConnector,
    formatter: Formatter,
    native_resources: List[BaseModel],
) -> List[BaseModel]:
    """
    Generic formatter:

    - If `formatter` is provided:
        * apply it on each native resource
        * accepted outputs:
            - a Pydantic model (native or unified)
            - a dict (e.g. from build_mapping_formatter)
        * dict outputs are wrapped into the target's native model
          for the given resource type.

    - Else: use unified path:
        origin-native -> UnifiedJob/UnifiedProfile -> target-native
    """
    if not native_resources:
        return []

    # -------- CASE 1: explicit formatter provided --------
    if formatter is not None:
        out_list: List[BaseModel] = []

        # choose target native class per resource
        if resource == Resource.JOB:
            target_cls = target.job_native_cls
        elif resource == Resource.PROFILE:
            target_cls = target.profile_native_cls
        else:
            raise ValueError(
                f"Unsupported resource in safe_format_resources: {resource}"
            )

        for r in native_resources:
            out = formatter(r)

            if isinstance(out, BaseModel):
                # Already a model: assume it's either native or unified
                out_list.append(out)
            elif isinstance(out, dict):
                # Mapping-based formatter: build target native model from dict
                out_list.append(target_cls(**out))
            else:
                raise TypeError(
                    f"Formatter returned unsupported type {type(out)}. "
                    f"Expected BaseModel or dict."
                )

        return out_list

    # -------- CASE 2: no formatter → unified path --------
    if resource == Resource.JOB:
        unified_list = [origin.to_unified_job(r) for r in native_resources]
        return [target.from_unified_job(u) for u in unified_list]

    if resource == Resource.PROFILE:
        unified_list = [origin.to_unified_profile(r) for r in native_resources]
        return [target.from_unified_profile(u) for u in unified_list]

    raise ValueError(f"Unsupported resource in safe_format_resources: {resource}")


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
    # TODO extend with more ops (startswith, endswith, regex, etc.)
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
    via BaseActions._request().
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

# --- CURSOR HELPERS ---


def get_cursor_native_name(
    resource: Union[BaseModel, Type[BaseModel]],
    cursor_mode: CursorMode,
) -> str:
    """
    Return the *native field name* (e.g. 'CreatedAt') whose metadata has
    json_schema_extra['cursor'] == mode.value (e.g. 'created_at').
    """
    # Normalize to class
    if isinstance(resource, BaseModel):
        resource_cls = type(resource)
    else:
        resource_cls = resource

    target_tag = cursor_mode.value  # "created_at", "updated_at", "id"

    fields_map = getattr(resource_cls, "model_fields", None) or getattr(
        resource_cls, "__fields__", {}
    )

    for name, f in fields_map.items():
        extra = getattr(f, "json_schema_extra", None)
        if not extra and hasattr(f, "field_info"):
            extra = getattr(f.field_info, "extra", None)

        if extra and extra.get("cursor") == target_tag:
            # 👇 Here `name` is the Python attribute name, e.g. "CreatedAt"
            return name

    raise ValueError(
        f"No field with cursor={target_tag!r} on model {resource_cls.__name__}"
    )


def get_cursor_native_value(resource: BaseModel, cursor_mode: CursorMode) -> Any:
    """
    Return the value of that native cursor field on the given instance.
    """
    field_name = get_cursor_native_name(resource, cursor_mode)
    return getattr(resource, field_name)


# --- BUILD QUERY PARAMS FROM WHERE HELPERS ---

#fixme update function based on the models.py
def build_cursor_query_params(
    cursor: Cursor,
    resource: Union[BaseModel, Type[BaseModel]],
    sort_by_native_name: Optional[str],
    sort_by_native_value: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Construit les query params de pagination/cursor à partir :

      - du Cursor (mode, start, end, sort_by)
      - des metadata du champ cursor dans le modèle :

        "cursor": CursorMode.CREATED_AT.value,
        "cursor_start_min": "date_range_min",
        "cursor_end_max": "date_range_max",
        "cursor_order_up": "asc",
        "cursor_order_down": "desc"

    ⚠️ Aucun fallback {field}_gte / {field}_lte :
       - si `cursor_start_min` ou `cursor_end_max` manquent et qu'on veut
         utiliser start/end, on lève une ValueError.
    """
    # Normaliser en classe
    resource_cls = type(resource) if isinstance(resource, BaseModel) else resource

    # 1) Trouver le champ natif qui porte le tag "cursor"
    cursor_field_name = get_cursor_native_name(resource_cls, cursor.mode)
    if not cursor_field_name:
        raise ValueError(
            f"No cursor field found for mode {cursor.mode} on resource {resource_cls.__name__}"
        )

    # 2) Récupérer les metadata sur ce champ
    field = resource_cls.model_fields.get(cursor_field_name) or getattr(
        resource_cls, "__fields__", {}
    ).get(cursor_field_name)

    extra = getattr(field, "json_schema_extra", None)
    if not extra and hasattr(field, "field_info"):  # compat pydantic v1
        extra = getattr(field.field_info, "extra", None)
    extra = extra or {}

    start_min_param = extra.get("cursor_start_min")
    end_max_param = extra.get("cursor_end_max")

    # Si on veut utiliser un cursor (start ou end), ces deux clés doivent exister
    if (cursor.start is not None or cursor.end is not None) and (
        not start_min_param or not end_max_param
    ):
        raise ValueError(
            f"Missing 'cursor_start_min' or 'cursor_end_max' in json_schema_extra "
            f"for cursor field '{cursor_field_name}' on {resource_cls.__name__}"
        )

    # Valeurs de direction officielles pour ce backend
    order_up = str(extra.get("cursor_order_up", "asc")).lower()
    order_down = str(extra.get("cursor_order_down", "desc")).lower()

    params: Dict[str, Any] = {}

    # 3) Paramètre de tri (facultatif)
    if sort_by_native_name and sort_by_native_value is not None:
        params[sort_by_native_name] = sort_by_native_value

    # 4) Appliquer le cursor.start / cursor.end
    sort_dir = str(getattr(cursor, "sort_by", order_up) or order_up).lower()

    # start
    if cursor.start is not None:
        if sort_dir == order_up:
            params[start_min_param] = cursor.start
        elif sort_dir == order_down:
            params[end_max_param] = cursor.start
        else:
            raise ValueError(
                f"Unknown cursor.sort_by direction '{cursor.sort_by}', "
                f"expected '{order_up}' or '{order_down}'"
            )

    # end
    if cursor.end is not None:
        if sort_dir == order_up:
            params[end_max_param] = cursor.end
        elif sort_dir == order_down:
            params[start_min_param] = cursor.end
        else:
            raise ValueError(
                f"Unknown cursor.sort_by direction '{cursor.sort_by}', "
                f"expected '{order_up}' or '{order_down}'"
            )

    return params




def build_eq_query_params(
    where: Optional[List[Condition]],
) -> Dict[str, Any]:
    """
    Transform a list of `Condition` into HTTP query params,
    but ONLY for EQ operators.

    - Only conditions with `op == Operator.EQ` are kept.
    - Key is the raw field name: `field=value`.
    - Non-EQ operators are ignored.
    """

    if not where:
        return {}

    params: Dict[str, Any] = {}

    for cond in where:
        if cond.op != Operator.EQ:
            # ignore GT, GTE, LT, LTE, IN, CONTAINS, ...
            continue

        key = cond.field
        params[key] = cond.value

    return params


def _get_search_binding(
    resource: Union[BaseModel, Type[BaseModel]],
    field_name: str,
) -> Optional[Dict[str, Any]]:
    """
    Read `json_schema_extra["search_binding"]` for a given resource field.
    """
    # Normalize to class
    if isinstance(resource, BaseModel):
        resource_cls = type(resource)
    else:
        resource_cls = resource
    model_field = resource_cls.model_fields.get(field_name)
    if not model_field:
        return None

    extra = model_field.json_schema_extra or {}
    binding = extra.get("search_binding")
    if not binding:
        return None

    return binding


def _normalize_values_as_list(value: Any) -> List[str]:
    """
    Turn a value into a list of strings.
    - If list/tuple/set -> list of str
    - Else -> single-element list
    """
    if isinstance(value, (list, tuple, set)):
        return [str(v) for v in value]
    return [str(value)]


def build_search_query_params(
    where: Optional[List[Condition]] = None,
    resource: Union[BaseModel, Type[BaseModel]] = None,
) -> Dict[str, Any]:
    """
    Aggregate CONTAINS conditions mapped via `search_binding`
    into one or more search field query params.

    Expected metadata on fields (json_schema_extra["search_binding"]):

      - "search_field": str
            Name of the query param (e.g. "keywords").

      - "field_join": "and" | "or"
            How this FIELD's expression combines with other fields
            mapped to the same search_field.
            Example:
              name.field_join = OR
              text.field_join = AND
            => "(name_expr) OR (text_expr)" or "(name_expr) AND (text_expr)"

      - "value_join": "and" | "or"
            How multiple values inside THIS field combine.
            If cond.value is ["data", "science"] and value_join="or":
              field_expr = "(data OR science)"
            If value_join="and":
              field_expr = "(data AND science)"
    """

    if not where or resource is None:
        return {}

    # Normalize to class
    resource_cls = type(resource) if isinstance(resource, BaseModel) else resource

    # search_field -> {"or": [expr...], "and": [expr...]}
    per_search_field: Dict[str, Dict[str, List[str]]] = {}

    for cond in where:
        if cond.op != Operator.CONTAINS:
            continue

        binding = _get_search_binding(resource_cls, cond.field)
        if not binding:
            # this field is not mapped to a search_field
            continue

        search_field = binding.get("search_field")
        if not search_field:
            # malformed binding, skip
            continue

        # How this FIELD combines with other fields for the same search_field
        field_join_raw = str(
            binding.get("field_join", BoolJoin.OR.value)
        ).lower()

        # How multiple VALUES inside this field combine
        value_join_raw = str(
            binding.get("value_join", BoolJoin.AND.value)
        ).lower()

        field_join = BoolJoin.AND if field_join_raw == BoolJoin.AND.value else BoolJoin.OR
        value_join = BoolJoin.AND if value_join_raw == BoolJoin.AND.value else BoolJoin.OR

        values = _normalize_values_as_list(cond.value)
        if not values:
            continue

        # Build this field's expression: e.g. "(python AND sql)" or "data"
        if len(values) == 1:
            field_expr = values[0]
        else:
            sep = " AND " if value_join == BoolJoin.AND else " OR "
            field_expr = "(" + sep.join(values) + ")"

        buckets = per_search_field.setdefault(
            search_field,
            {"or": [], "and": []},
        )

        if field_join == BoolJoin.AND:
            buckets["and"].append(field_expr)
        else:
            buckets["or"].append(field_expr)

    # Assemble final query params per search_field
    result: Dict[str, Any] = {}

    for search_field, groups in per_search_field.items():
        or_groups = groups["or"]
        and_groups = groups["and"]

        if not or_groups and not and_groups:
            continue

        parts: List[str] = []

        # OR block (fields whose field_join == OR)
        if or_groups:
            if len(or_groups) == 1:
                parts.append(or_groups[0])
            else:
                parts.append("(" + " OR ".join(or_groups) + ")")

        # AND block (fields whose field_join == AND)
        if and_groups:
            and_block = (
                and_groups[0]
                if len(and_groups) == 1
                else "(" + " AND ".join(and_groups) + ")"
            )
            parts.append(and_block)

        if not parts:
            continue

        value = " AND ".join(parts)
        result[search_field] = value

    return result


## WHERE FILTER HELPERS ---


InFormatter = Callable[[str, List[Any]], Any]

def _array_formatter(param: str, values: List[Any]) -> List[Any]:
    """Default: keep as a Python list."""
    return values


def _csv_formatter(param: str, values: List[Any]) -> str:
    """Comma-separated string: 'A,B,C'."""
    return ",".join(str(v) for v in values)


def _array_string_formatter(param: str, values: List[Any]) -> str:
    """
    JSON-encoded array as a string: '["A","B","C"]'.
    Useful if the API expects a stringified array in the query.
    """
    return json.dumps(values)


IN_BINDING_FORMATTERS: Dict[str, InFormatter] = {
    "array": _array_formatter,           # ✅ default
    "csv": _csv_formatter,
    "array_string": _array_string_formatter,
}



def _get_in_binding(
    resource: Type[BaseModel],
    field_name: str,
) -> Optional[Dict[str, Any]]:
    model_field = resource.model_fields.get(field_name)
    if not model_field:
        return None

    extra = model_field.json_schema_extra or {}
    return extra.get("in_binding")


def build_in_query_params(
    where: Optional[List[Condition]],
    resource: Type[BaseModel],
) -> Dict[str, Any]:
    """
    Build query params for all IN conditions on `resource`.

    Per-field metadata (in `json_schema_extra["in_binding"]`):

      - "query_field":      optional query param name
      - "formatter":  one of:
            - "array"        -> default, returns Python list
            - "csv"          -> "A,B,C"
            - "array_string" -> '["A","B","C"]'

    If "query_field" is omitted, we use the **field__in pattern**:
        query_field = f"{field}__in"
    """

    if not where:
        return {}

    # Accept instance or class
    if isinstance(resource, BaseModel):
        resource_cls = type(resource)
    else:
        resource_cls = resource

    # query_field -> (values, formatter_key)
    grouped_values: Dict[str, List[Any]] = {}
    formatter_per_param: Dict[str, str] = {}

    for cond in where:
        if cond.op != Operator.IN:
            continue

        binding = _get_in_binding(resource_cls, cond.field)

        # --- query_field name: explicit or field__in pattern ---
        if binding and "query_field" in binding:
            query_field = binding["query_field"]
        else:
            # named pattern: "field__in"
            query_field = f"{cond.field}__in"

        # --- formatter: default "array" if not specified ---
        if binding and "formatter" in binding:
            fmt_key = binding["formatter"]
        else:
            fmt_key = "array"  # default formatting is array ✅

        # normalize values to list
        value = cond.value
        if isinstance(value, (list, tuple, set)):
            values_list = list(value)
        else:
            values_list = [value]

        if not values_list:
            continue

        grouped_values.setdefault(query_field, []).extend(values_list)
        # last one wins if inconsistent, but usually it's the same
        formatter_per_param[query_field] = fmt_key

    if not grouped_values:
        return {}

    params: Dict[str, Any] = {}

    for query_field, values in grouped_values.items():
        fmt_key = formatter_per_param.get(query_field, "array")
        formatter = IN_BINDING_FORMATTERS.get(fmt_key)

        if formatter is None:
            raise ValueError(
                f"Unknown IN formatter '{fmt_key}' for query_field '{query_field}'"
            )

        params[query_field] = formatter(query_field, values)

    return params


def build_connector_params(
    resource_cls: Type[BaseModel],
    where: Optional[List[Condition]],
    cursor: Optional[Cursor],
    *,
    sort_by_unified: Optional[str],
    sort_param_name: Optional[str],
) -> Dict[str, Any]:
    """
    Fonction utilitaire générique pour construire les query params envoyés
    au connecteur HTTP à partir de :

      - resource_cls : modèle natif du connecteur (ex: WarehouseAJob)
      - where        : liste de Condition (EQ, IN, CONTAINS, etc.)
      - cursor       : objet Cursor (start, end, mode, sort_by)
      - sort_by_unified : nom du champ unifié (ex: "created_at")
      - sort_param_name : nom du param HTTP pour le tri (ex: "order", "sort_by")

    Cette fonction orchestre :
      - build_eq_query_params    (EQ simples)
      - build_in_query_params    (IN + in_binding)
      - build_search_query_params (CONTAINS + search_binding)
      - build_cursor_query_params (cursor_* metadata)
    """

    where = where or []
    params: Dict[str, any] = {}

    # 1) Filtres simples (EQ / GT / GTE / LT / LTE / CONTAINS "field__xxx")
    params.update(build_eq_query_params(where))

    # 2) IN avec in_binding + formatter (board_key -> board_keys, tags -> tags, ...)
    params.update(build_in_query_params(where=where, resource=resource_cls))

    # 3) SEARCH (keywords / tags...) via search_binding
    params.update(build_search_query_params(where=where, resource=resource_cls))

    # 4) CURSOR via metadata cursor_* sur le modèle
    if cursor is not None:
        params.update(
            build_cursor_query_params(
                cursor=cursor,
                resource=resource_cls,
                sort_by_native_name=sort_param_name,
                sort_by_native_value=sort_by_unified,
            )
        )

    return params
