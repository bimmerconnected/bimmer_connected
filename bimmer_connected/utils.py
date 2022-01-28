"""General utils and base classes used in the library."""

import datetime
import inspect
import json
import logging
import sys
import traceback
from abc import ABC
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from typing import Callable, TypeVar

    from typing_extensions import Concatenate, ParamSpec

    _T = TypeVar("_T")
    _R = TypeVar("_R")
    _P = ParamSpec("_P")
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
            k: v
            for k, v in obj.__dict__.items()
            if k not in excluded and ((exclude_hidden and not str(k).startswith("_")) or not exclude_hidden)
        },
        **{a: getattr(obj, a) for a in get_class_property_names(obj) if a not in excluded + ["to_json"]},
    )


def get_class_property_names(obj: object):
    """Returns the names of all properties of a class."""
    return [p[0] for p in inspect.getmembers(type(obj), inspect.isdatadescriptor) if not p[0].startswith("_")]


def to_json(obj: object, *args, **kwargs):
    """Serialize a nested object to json. Tries to call `to_json` attribute on object first."""

    def serialize(obj: object):
        if hasattr(obj, "as_dict"):
            return getattr(obj, "as_dict")()
        if hasattr(obj, "__dict__"):
            return {k: v for k, v in getattr(obj, "__dict__").items() if not k.startswith("_")}
        return str(obj)

    return json.dumps(obj, default=serialize, *args, **kwargs)


def parse_datetime(date_str: str) -> Optional[datetime.datetime]:
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

    def as_dict(self) -> dict:
        """Return all attributes and parameters."""
        return serialize_for_json(self)


def deprecated(replacement: str = None):
    """Mark a function or property as deprecated."""

    def decorator(func: "Callable[Concatenate[_T, _P], _R]") -> "Callable[Concatenate[_T, _P], _R | None]":
        def _func_wrapper(self: "_T", *args: "_P.args", **kwargs: "_P.kwargs") -> "_R | None":
            # warnings.simplefilter('always', DeprecationWarning)  # turn off filter
            replacement_text = f" Please change to '{replacement}'." if replacement else ""
            # warnings.warn(f"{func.__qualname__} is deprecated.{replacement_text}",
            # category=DeprecationWarning,
            # stacklevel=2)
            # warnings.simplefilter('default', DeprecationWarning)  # reset filter
            stack = traceback.extract_stack()[-2]
            _LOGGER.warning(
                "DeprecationWarning:%s:%s: '%s' is deprecated.%s",
                stack.filename,
                stack.lineno,
                func.__qualname__,
                replacement_text,
            )
            return func(self, *args, **kwargs)

        return _func_wrapper

    return decorator
