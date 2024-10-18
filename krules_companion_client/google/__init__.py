import inspect
import json
import os
import uuid
from datetime import datetime
from datetime import timezone
from typing import List, Tuple, Any
from typing import Sequence, Callable

from cloudevents.pydantic import CloudEvent
from google.cloud import pubsub_v1
from pydantic import BaseModel, PositiveInt, model_validator

from krules_companion_client import __version__
from krules_companion_client.commands import _validate_filter


class ScheduleCallbackBase(BaseModel):
    when: datetime | None = None
    rnd_delay: int | None = None
    seconds: PositiveInt | None = None
    now: bool | None = None
    channels: List[str] = []
    message: str = ""
    fresh_data: bool | None = False

    @model_validator(mode='after')
    def validate_all(self) -> 'ScheduleCallbackBase':
        assert sum(p is not None for p in [self.when, self.seconds, self.now]) == 1, "Specify one of when, seconds, now"
        assert len(self.channels) > 0, "At least one channel must be specified"

        return self


class ScheduleCallbackSingleRequest(ScheduleCallbackBase):
    replace_id: str | None = None


class ScheduleCallbackMultiRequest(ScheduleCallbackBase):
    filter: Tuple[str, str, Any] | None = None


class _JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if inspect.isfunction(obj):
            return obj.__name__
        elif isinstance(obj, object):
            return str(type(obj))
        return json.JSONEncoder.default(self, obj)


def _callback(publish_future, exception_handler=None):
    try:
        publish_future.result(timeout=0)
    except Exception as ex:
        if exception_handler is not None:
            exception_handler(ex)
        else:
            raise


class PubsubClient(object):

    def __init__(self, topic_path: str = None, scheduler_topic_path: str = None, subscription: str = None,
                 client: pubsub_v1.PublisherClient = None):

        if client is None:
            self.client = pubsub_v1.PublisherClient()
        else:
            self.client = client

        if topic_path is None:
            self.topic_path = os.environ.get('COMPANION_INGESTION_TOPIC')
        else:
            self.topic_path = topic_path

        if scheduler_topic_path is None:
            self.scheduler_topic_path = os.environ.get('COMPANION_SCHEDULER_TOPIC')
        else:
            self.scheduler_topic_path = scheduler_topic_path

        if not any([self.topic_path, self.scheduler_topic_path]):
            raise ValueError(
                'Any of COMPANION_INGESTION_TOPIC or COMPANION_SCHEDULER_TOPIC environment variables must be set')

        if subscription is None:
            self.subscription = os.environ.get('COMPANION_SUBSCRIPTION')
        if self.subscription is None:
            raise ValueError("Subscription is required, check the COMPANION_SUBSCRIPTION environment variable")

        if "CE_SOURCE" in os.environ:
            self.source = os.environ.get('CE_SOURCE')
        else:
            self.source = f"CompanionClient/{__version__}"

    def publish(self, group: str = None, entity: str = None, filters: Sequence[Tuple[str, str, Any]] = (),
                properties: dict = None,
                exception_handler: Callable = None, **properties_kwargs) -> None:

        if filters is None:
            filters = []
        has_filters = len(filters) > 0

        if group is None:
            raise ValueError("group cannot be None")
        if entity is None and not has_filters:
            raise ValueError("one of entity or filters must be provided")

        if has_filters and len(filters) > 1:
            raise ValueError("currently, only a single filter is supported")

        if properties is None:
            properties = {}
        properties.update(properties_kwargs)

        if "_last_update" not in properties:
            properties["_last_update"] = f"dt|{datetime.utcnow().isoformat()}"

        event_type: str | None = None
        subject: str | None = None
        payload: dict = {}

        _id = str(uuid.uuid4())
        if has_filters:
            event_type = "io.krules.streams.group.v1.data"
            subject = f'group|{self.subscription}|{group}'
            filter = _validate_filter(filters[0])
            payload = {
                "data": properties,
                "entities_filter": filter,
            }
        else:
            event_type = "io.krules.streams.entity.v1.data"
            subject = f'entity|{self.subscription}|{group}|{entity}'
            payload = {
                "data": properties,
            }

        ext_props = {}
        ext_props['originid'] = _id  # TODO: #869394akv
        ext_props["subscription"] = self.subscription
        ext_props["group"] = group

        event = CloudEvent(
            id=_id,
            type=event_type,
            source=self.source,
            subject=subject,
            data=payload,
            time=datetime.now(timezone.utc),
            datacontenttype="application/json",
            # dataschema=dataschema,
        )

        event_obj = event.model_dump(exclude_unset=True, exclude_none=True)
        event_obj["data"] = json.dumps(event_obj["data"], cls=_JSONEncoder).encode()
        event_obj["time"] = event_obj["time"].isoformat()

        future = self.client.publish(self.topic_path, **event_obj, **ext_props, contentType="text/json")
        future.add_done_callback(lambda _future: _callback(_future, exception_handler))

    def delete(self, group: str, entity: str, exception_handler: Callable = None):
        if group is None:
            raise ValueError("group cannot be None")
        if entity is None:
            raise ValueError("entity cannot be None")

        _id = str(uuid.uuid4())
        event_type = "io.krules.streams.entity.v1.delete"
        subject = f'entity|{self.subscription}|{group}|{entity}'

        ext_props = {}
        ext_props['originid'] = _id  # TODO: #869394akv
        ext_props["subscription"] = self.subscription
        ext_props["group"] = group

        event = CloudEvent(
            id=_id,
            type=event_type,
            source=self.source,
            subject=subject,
            data={},
            time=datetime.now(timezone.utc),
            datacontenttype="application/json",
        )

        event_obj = event.model_dump(exclude_unset=True, exclude_none=True)
        event_obj["data"] = json.dumps(event_obj["data"], cls=_JSONEncoder).encode()
        event_obj["time"] = event_obj["time"].isoformat()

        future = self.client.publish(self.topic_path, **event_obj, **ext_props, contentType="text/json")
        future.add_done_callback(lambda _future: _callback(_future, exception_handler))

    def delete_all(self, group: str, exception_handler: Callable = None):
        if group is None:
            raise ValueError("group cannot be None")

        _id = str(uuid.uuid4())
        event_type = "io.krules.streams.group.v1.delete"
        subject = f'group|{self.subscription}|{group}'

        ext_props = {}
        ext_props['originid'] = _id  # TODO: #869394akv
        ext_props["subscription"] = self.subscription
        ext_props["group"] = group

        event = CloudEvent(
            id=_id,
            type=event_type,
            source=self.source,
            subject=subject,
            data={},
            time=datetime.now(timezone.utc),
            datacontenttype="application/json",
        )

        event_obj = event.model_dump(exclude_unset=True, exclude_none=True)
        event_obj["data"] = json.dumps(event_obj["data"], cls=_JSONEncoder).encode()
        event_obj["time"] = event_obj["time"].isoformat()

        future = self.client.publish(self.topic_path, **event_obj, **ext_props, contentType="text/json")
        future.add_done_callback(lambda _future: _callback(_future, exception_handler))

    def callback(self, group: str = None, entity: str = None, filters: Sequence[Tuple[str, str, Any]] = (),
                 when: datetime = None, seconds: int = None, now: bool = None,
                 channels: Sequence[str] = None, replace_id: str = None, rnd_delay: int = None,
                 fresh: bool = False,
                 message: str = "",
                 exception_handler: Callable = None
                 ):

        if filters is None:
            filters = []
        has_filters = len(filters) > 0

        if group is None:
            raise ValueError("group cannot be None")
        #if entity is None and not has_filters:
        #    raise ValueError("one of entity or filters must be provided")

        if has_filters and len(filters) > 1:
            raise ValueError("currently, only a single filter is supported")

        _id = str(uuid.uuid4())
        task_id = f"{self.subscription}|{str(uuid.uuid4())}"

        ext_props = {}
        ext_props['originid'] = _id  # TODO: #869394akv
        ext_props["subscription"] = self.subscription
        ext_props["group"] = group

        if entity is None:
            req = ScheduleCallbackMultiRequest(
                when=when,
                seconds=seconds,
                now=now,
                channels=channels,
                rnd_delay=rnd_delay,
                fresh=fresh,
                message=message,
                filter=has_filters and filters[0] or None
            )
            event_type = "io.krules.streams.group.v1.schedule"
            subject = f'group|{self.subscription}|{group}'

        else:
            req = ScheduleCallbackSingleRequest(
                when=when,
                seconds=seconds,
                now=now,
                channels=channels,
                rnd_delay=rnd_delay,
                fresh=fresh,
                message=message,
                replace_id=replace_id,
            )
            event_type = "io.krules.streams.entity.v1.schedule"
            subject = f'entity|{self.subscription}|{group}|{entity}'

        event = CloudEvent(
            id=_id,
            type=event_type,
            source=self.source,
            subject=subject,
            data={
                "task_id": task_id,
                "data": req.model_dump(),
            },
            time=datetime.now(timezone.utc),
            datacontenttype="application/json",
        )

        event_obj = event.model_dump(exclude_unset=True, exclude_none=True)
        event_obj["data"] = json.dumps(event_obj["data"], cls=_JSONEncoder).encode()
        event_obj["time"] = event_obj["time"].isoformat()

        future = self.client.publish(self.scheduler_topic_path, **event_obj, **ext_props, contentType="text/json")
        future.add_done_callback(lambda _future: _callback(_future, exception_handler))
