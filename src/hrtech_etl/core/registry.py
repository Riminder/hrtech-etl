# core/registry.py
from typing import Dict, Type, Optional, Callable
from pydantic import BaseModel
from .connector import BaseConnector
from .types import WarehouseType


class ConnectorMeta(BaseModel):
    name: str
    label: str
    warehouse_type: WarehouseType
    job_model: str  # e.g. "hrtech_etl.connectors.warehouse_a.models.WarehouseAJob"
    profile_model: str  # e.g. "hrtech_etl.connectors.warehouse_a.models.WarehouseAProfile"
    factory: Optional[str] = None  # e.g. "hrtech_etl.connectors.warehouse_a.WarehouseAConnector.build_default"
    connector_path: str  # e.g. "hrtech_etl.connectors.warehouse_a.WarehouseAConnector"


_CONNECTORS: Dict[str, ConnectorMeta] = {}
_CONNECTOR_INSTANCES: Dict[str, BaseConnector] = {}  # simple cache if you want
_FACTORIES: Dict[str, Callable[[], BaseConnector]] = {}


def register_connector(
        meta: ConnectorMeta,
        factory: Optional[Callable[[], BaseConnector]] = None,
     ) -> None:
    """Register a connector by its metadata.
    If a factory is provided, it will be used to create connector instances.
    """
    if meta.name in _CONNECTORS:
        raise ValueError(f"Connector with name {meta.name!r} is already registered.")
    
    _CONNECTORS[meta.name] = meta
    if factory is not None:
        _FACTORIES[meta.name] = factory

def list_connectors() -> Dict[str, ConnectorMeta]:
    return _CONNECTORS


def get_connector_instance(name: str) -> BaseConnector:
    # TODO: inject auth/actions here as you see fit
    try:
        factory = _FACTORIES[name]
    except KeyError:
        raise KeyError(f"No factory registered for connector {name!r}")
    return factory()

