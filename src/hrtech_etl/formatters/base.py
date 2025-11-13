# src/hrtech_etl/formatters/base.py
from typing import Protocol, TypeVar

from pydantic import BaseModel

JIn = TypeVar("JIn", bound=BaseModel)
JOut = TypeVar("JOut", bound=BaseModel)
PIn = TypeVar("PIn", bound=BaseModel)
POut = TypeVar("POut", bound=BaseModel)


class JobFormatter(Protocol[JIn, JOut]):
    def __call__(self, job: JIn) -> JOut: ...


class ProfileFormatter(Protocol[PIn, POut]):
    def __call__(self, profile: PIn) -> POut: ...
