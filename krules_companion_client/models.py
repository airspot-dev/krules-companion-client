from datetime import datetime
from enum import Enum
from types import NoneType
from typing import Generic, TypeVar, Sequence, Any

from pydantic import BaseModel, model_validator

T = TypeVar("T")


class EventType(str, Enum):
    EntityCreated = "io.krules.streams.entity.v1.created"
    EntityUpdated = "io.krules.streams.entity.v1.updated"
    EntityDeleted = "io.krules.streams.entity.v1.deleted"
    EntityCallback = "io.krules.streams.entity.v1.callback"


class BaseUpdateEvent(BaseModel):

    @model_validator(mode='before')
    @classmethod
    def assign_id_to_state(cls, data: Any) -> Any:
        state = data.get('state', {})
        if isinstance(state, dict):
            if len(state) and 'id' not in state:
                state['id'] = data['id']
            else:
                data['state'] = None

        old_state = data.get('old_state', {})
        if isinstance(state, dict):
            if len(old_state) and 'id' not in old_state:
                old_state['id'] = data['id']
            else:
                data['old_state'] = None

        return data


class EntityUpdatedEvent(BaseUpdateEvent, Generic[T]):
    id: str
    group: str
    subscription: int
    changed_properties: Sequence[str]
    state: T
    old_state: T | None = None


class EntityCreatedEvent(BaseUpdateEvent, Generic[T]):
    id: str
    group: str
    subscription: int
    changed_properties: Sequence[str]
    state: T
    old_state: NoneType


class EntityDeletedEvent(BaseUpdateEvent, Generic[T]):
    id: str
    group: str
    subscription: int
    changed_properties: Sequence[str]
    state: NoneType
    old_state: T


class EntityCallbackEvent(BaseUpdateEvent, Generic[T]):
    last_updated: datetime
    task_id: str
    id: str
    group: str
    subscription: int
    state: T
    message: str
