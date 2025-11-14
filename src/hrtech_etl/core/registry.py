# core/registry.py
from typing import Dict, Type, Optional
from pydantic import BaseModel
from .connector import BaseConnector
from .models import UnifiedJob, UnifiedProfile
from .types import WarehouseType


class ConnectorMeta(BaseModel):
    name: str
    label: str
    warehouse_type: WarehouseType
    connector_path: str  # e.g. "hrtech_etl.connectors.warehouse_a.WarehouseAConnector"


_CONNECTORS: Dict[str, ConnectorMeta] = {}
_CONNECTOR_INSTANCES: Dict[str, BaseConnector] = {}  # simple cache if you want


def register_connector(meta: ConnectorMeta) -> None:
    _CONNECTORS[meta.name] = meta


def list_connectors() -> Dict[str, ConnectorMeta]:
    return _CONNECTORS


def get_connector_instance(name: str) -> BaseConnector:
    if name in _CONNECTOR_INSTANCES:
        return _CONNECTOR_INSTANCES[name]

    meta = _CONNECTORS.get(name)
    if not meta:
        raise KeyError(f"Unknown connector name: {name!r}")

    module_name, _, class_name = meta.connector_path.rpartition(".")
    module = __import__(module_name, fromlist=[class_name])
    cls = getattr(module, class_name)

    # TODO: inject auth/actions here as you see fit
    instance: BaseConnector = cls.build_default()  # you can define a @classmethod on the connector
    _CONNECTOR_INSTANCES[name] = instance
    return instance
