import os
from datetime import datetime
from pathlib import Path
from typing import Sequence, Tuple, Any

from krules_companion_client.commands import config, publish, callback, delete, delete_all


class HttpClient(object):

    def __init__(self, **config_kwargs):

        if "config" not in config_kwargs:
            if "COMPANION_CONFIG" in os.environ or "COMPANION_CONFIG_PATH" in os.environ:
                config_kwargs["config"] = Path(os.environ.get("COMPANION_CONFIG", os.environ["COMPANION_CONFIG_PATH"]))
        if "address" not in config_kwargs:
            if "COMPANION_ADDRESS" in os.environ:
                config_kwargs["address"] = os.environ["COMPANION_ADDRESS"]
        if "subscription" not in config_kwargs:
            if "COMPANION_SUBSCRIPTION" in os.environ:
                config_kwargs["subscription"] = os.environ["COMPANION_SUBSCRIPTION"]
        if "api_key" not in config_kwargs:
            if "COMPANION_APIKEY" in os.environ:
                config_kwargs["api_key"] = os.environ["COMPANION_APIKEY"]

        config(**config_kwargs)

    @staticmethod
    def publish(group: str = None, entity: str = None, filters: Sequence[Tuple[str, str, Any]] = (),
                properties: dict = None, **properties_kwargs):

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

        if has_filters:
            publish(group, filter=filters[0], properties=[properties])
        else:
            publish(group, entity, properties=[properties])

    @staticmethod
    def delete(group: str, entity: str):
        delete(group, entity)

    @staticmethod
    def delete_all(group: str):
        delete_all(group, True)

    @staticmethod
    def callback(group: str = None, entity: str = None, filters: Sequence[Tuple[str, str, Any]] = (),
                 when: datetime = None, seconds: int = None, now: bool = None,
                 channels: Sequence[str] = None, replace_id: str = None, rnd_delay: int = None,
                 fresh: bool = False,
                 message: str = False
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

        if has_filters:
            callback(group, entity, filters[0], when, seconds, now, channels, replace_id, rnd_delay, fresh, message)
        else:
            callback(group, entity, (None, None, None), when, seconds, now, channels, replace_id, rnd_delay, fresh, message)
