"""General utils and base classes used in the library."""

from abc import ABC
import datetime
import inspect
import json
import logging
import sys

_LOGGER = logging.getLogger(__name__)


def serialize_for_json(obj: object, excluded: list = None, exclude_hidden: bool = True) -> dict:
    """
    Returns all object attributes and properties as dictionary.

    :param excluded list: attributes and parameters NOT to export
    :param exclude_hidden bool: if true, do not export attributes or parameters starting with '_'
    """
    excluded = excluded if excluded else []
    return dict(
        {
            k: v for k, v in obj.__dict__.items()
            if k not in excluded and ((exclude_hidden and not str(k).startswith("_")) or not exclude_hidden)
        },
        **{a: getattr(obj, a) for a in get_class_property_names(obj) if a not in excluded + ["to_json"]}
    )


def get_class_property_names(obj: object):
    """Returns the names of all properties of a class."""
    return [
        p[0] for p in inspect.getmembers(type(obj), inspect.isdatadescriptor)
        if not p[0].startswith("_")
    ]


def to_json(obj: object, *args, **kwargs):
    """Serialize a nested object to json. Tries to call `to_json` attribute on object first."""
    def serialize(obj: object):
        return getattr(obj, 'to_json',  getattr(obj, '__dict__') if hasattr(obj, '__dict__') else str(obj))
    return json.dumps(obj, default=serialize, *args, **kwargs)


def parse_datetime(date_str: str) -> datetime.datetime:
    """Convert a time string into datetime."""
    if not date_str:
        return None
    date_formats = ["%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"]
    for date_format in date_formats:
        try:
            parsed = datetime.datetime.strptime(date_str, date_format)
            # Assume implicit UTC for Python 3.6
            if sys.version_info < (3, 7):
                parsed = parsed.replace(tzinfo=datetime.timezone.utc)
            return parsed
        except ValueError:
            pass
    _LOGGER.error("unable to parse '%s' using %s", date_str, date_formats)
    return None


class SerializableBaseClass(ABC):  # pylint: disable=too-few-public-methods
    """Base class to enable json-compatible serialization."""

    @property
    def to_json(self) -> dict:
        """Return all attributes and parameters."""
        return serialize_for_json(self)
