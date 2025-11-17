# core/expressions.py
from typing import Any, Iterable, Optional, Sequence, Type

from pydantic import BaseModel

from .types import Condition, Operator


class ConditionBuilder:
    def __init__(
        self, field_name: str, allowed_ops: Optional[Iterable[Operator]] = None
    ):
        self.field_name = field_name
        self.allowed_ops = set(allowed_ops) if allowed_ops is not None else None

    def _ensure_allowed(self, op: Operator) -> None:
        if self.allowed_ops is not None and op not in self.allowed_ops:
            raise ValueError(
                f"Operator {op.value!r} is not allowed on field {self.field_name!r}"
            )

    def eq(self, value: Any) -> Condition:
        op = Operator.EQ
        self._ensure_allowed(op)
        return Condition(field=self.field_name, op=op, value=value)

    def gt(self, value: Any) -> Condition:
        op = Operator.GT
        self._ensure_allowed(op)
        return Condition(field=self.field_name, op=op, value=value)

    def gte(self, value: Any) -> Condition:
        op = Operator.GTE
        self._ensure_allowed(op)
        return Condition(field=self.field_name, op=op, value=value)

    def lt(self, value: Any) -> Condition:
        op = Operator.LT
        self._ensure_allowed(op)
        return Condition(field=self.field_name, op=op, value=value)

    def lte(self, value: Any) -> Condition:
        op = Operator.LTE
        self._ensure_allowed(op)
        return Condition(field=self.field_name, op=op, value=value)

    def contains(self, value: Any) -> Condition:
        op = Operator.CONTAINS
        self._ensure_allowed(op)
        return Condition(field=self.field_name, op=op, value=value)

    def in_(self, values: Sequence[Any]) -> Condition:
        op = Operator.IN
        self._ensure_allowed(op)
        # store as list so it's JSON-serializable
        return Condition(field=self.field_name, op=op, value=list(values))


def Prefilter(model_cls: Type[BaseModel], field_name: str) -> ConditionBuilder:
    """
    Build a ConditionBuilder for a given model field, using its `prefilter`
    metadata in json_schema_extra.

    Example:
        from hrtech_etl.core.expressions import Prefilter

        where_jobs = [
            Prefilter(WarehouseAJob, "job_title").contains("engineer"),
            Prefilter(WarehouseAJob, "created_on").gte(my_date),
        ]
    """
    fields_map = getattr(model_cls, "model_fields", None) or getattr(
        model_cls, "__fields__", {}
    )

    if field_name not in fields_map:
        raise AttributeError(f"{model_cls.__name__} has no field {field_name!r}")

    f = fields_map[field_name]

    # pydantic v1/v2 compatibility for extra metadata
    extra = getattr(f, "json_schema_extra", None)
    if not extra and hasattr(f, "field_info"):
        extra = getattr(f.field_info, "extra", None)
    extra = extra or {}

    prefilter_meta = extra.get("prefilter") or {}

    # If no prefilter metadata at all, this field is not usable in prefilter expressions
    if not prefilter_meta:
        raise ValueError(
            f"Field {field_name!r} on {model_cls.__name__} is not eligible for prefilter expressions"
        )

    ops_raw = prefilter_meta.get("operators") or []
    if not ops_raw:
        raise ValueError(
            f"Field {field_name!r} on {model_cls.__name__} has no prefilter operators defined"
        )

    allowed_ops = {Operator(op_str) for op_str in ops_raw}

    return ConditionBuilder(field_name, allowed_ops=allowed_ops)
