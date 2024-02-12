from datetime import datetime
from enum import Enum
from pydantic import BaseModel
from types import NoneType
from typing import Generic, TypeVar, Sequence

T = TypeVar("T")


class EventType(str, Enum):
    EntityCreated = "io.krules.streams.entity.v1.created"
    EntityUpdated = "io.krules.streams.entity.v1.updated"
    EntityDeleted = "io.krules.streams.entity.v1.deleted"
    EntityCallback = "io.krules.streams.entity.v1.callback"


class EntityUpdatedEvent(BaseModel, Generic[T]):
    id: str
    group: str
    subscription: int
    changed_properties: Sequence[str]
    state: T
    old_state: T | None = None


class EntityCreatedEvent(BaseModel, Generic[T]):
    id: str
    group: str
    subscription: int
    changed_properties: Sequence[str]
    state: T
    old_state: NoneType


class EntityDeletedEvent(BaseModel, Generic[T]):
    id: str
    group: str
    subscription: int
    changed_properties: Sequence[str]
    state: NoneType
    old_state: T


class EntityCallbackEvent(BaseModel, Generic[T]):
    last_updated: datetime
    task_id: str
    id: str
    group: str
    subscription: int
    state: T
    message: str
