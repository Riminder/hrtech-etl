# core/expressions.py
from typing import Any, Iterable, Optional, Type
from pydantic import BaseModel

from .types import Condition, Operator


class ConditionBuilder:
    def __init__(self, field_name: str, allowed_ops: Optional[Iterable[Operator]] = None):
        self.field_name = field_name
        self.allowed_ops = set(allowed_ops) if allowed_ops is not None else None

    def _ensure_allowed(self, op: Operator):
        if self.allowed_ops is not None and op not in self.allowed_ops:
            raise ValueError(
                f"Operator {op.value!r} is not allowed on field {self.field_name!r}"
            )

    def eq(self, value: Any) -> Condition:
        op = Operator.EQ
        self._ensure_allowed(op)
        return Condition(field=self.field_name, op=op, value=value)

    def gte(self, value: Any) -> Condition:
        op = Operator.GTE
        self._ensure_allowed(op)
        return Condition(field=self.field_name, op=op, value=value)

    def contains(self, value: Any) -> Condition:
        op = Operator.CONTAINS
        self._ensure_allowed(op)
        return Condition(field=self.field_name, op=op, value=value)

    # ... gt / lt / lte / is_in same pattern ...


def field(model_cls: Type[BaseModel], field_name: str) -> ConditionBuilder:
    fields_map = getattr(model_cls, "model_fields", None) or getattr(
        model_cls, "__fields__", {}
    )

    if field_name not in fields_map:
        raise AttributeError(f"{model_cls.__name__} has no field {field_name!r}")

    f = fields_map[field_name]
    extra = getattr(f, "json_schema_extra", None)
    if not extra and hasattr(f, "field_info"):
        extra = getattr(f.field_info, "extra", None)

    filter_meta = (extra or {}).get("filter") or {}
    if not filter_meta.get("eligible", False):
        raise ValueError(
            f"Field {field_name!r} on {model_cls.__name__} is not eligible for expressions"
        )

    ops_raw = filter_meta.get("operators") or []
    allowed_ops = {Operator(op_str) for op_str in ops_raw}

    return ConditionBuilder(field_name, allowed_ops=allowed_ops)
