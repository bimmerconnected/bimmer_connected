"""General utils and base classes used in the library."""


import datetime
import inspect
import json
import logging
import pathlib
import time
from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Optional, Union

from bimmer_connected.models import AnonymizedResponse

if TYPE_CHECKING:
    from typing import TypeVar

    from typing_extensions import ParamSpec

    _T = TypeVar("_T")
    _R = TypeVar("_R")
    _P = ParamSpec("_P")
_LOGGER = logging.getLogger(__name__)


JSON_IGNORED_KEYS = ["account", "_account", "vehicle", "_vehicle", "status", "remote_services"]


def get_class_property_names(obj: object):
    """Return the names of all properties of a class."""
    return [p[0] for p in inspect.getmembers(type(obj), inspect.isdatadescriptor) if not p[0].startswith("_")]


def parse_datetime(date_str: str) -> Optional[datetime.datetime]:
    """Convert a time string into datetime."""
    if not date_str:
        return None
    date_formats = ["%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"]
    for date_format in date_formats:
        try:
            # Parse datetimes using `time.strptime` to allow running in some embedded python interpreters.
            # https://bugs.python.org/issue27400
            time_struct = time.strptime(date_str, date_format)
            parsed = datetime.datetime(*(time_struct[0:6]))
            if time_struct.tm_gmtoff and time_struct.tm_gmtoff != 0:
                parsed = parsed - datetime.timedelta(seconds=time_struct.tm_gmtoff)
            parsed = parsed.replace(tzinfo=datetime.timezone.utc)
            return parsed
        except ValueError:
            pass
    _LOGGER.error("unable to parse '%s' using %s", date_str, date_formats)
    return None


class MyBMWJSONEncoder(json.JSONEncoder):
    """JSON Encoder that handles data classes, properties and additional data types."""

    def default(self, o) -> Union[str, dict]:  # noqa: D102
        if isinstance(o, (datetime.datetime, datetime.date, datetime.time)):
            return o.isoformat()
        if not isinstance(o, Enum) and hasattr(o, "__dict__") and isinstance(o.__dict__, Dict):
            retval: Dict = o.__dict__
            retval.update({p: getattr(o, p) for p in get_class_property_names(o)})
            return {k: v for k, v in retval.items() if k not in JSON_IGNORED_KEYS}
        return str(o)


def to_camel_case(input_str: str) -> str:
    """Convert SNAKE_CASE or snake_case to camelCase."""

    retval = ""
    flag_upper = False
    for curr in input_str.lower():
        if not curr.isalnum():
            if curr == "_":
                flag_upper = True
            continue
        retval = retval + (curr.upper() if flag_upper else curr)
        flag_upper = False
    return retval


def log_response_store_to_file(response_store: List[AnonymizedResponse], logfile_path: pathlib.Path) -> None:
    """Log all responses to files."""

    for response in response_store:
        output_path = logfile_path / response.filename
        content = response.content

        with open(output_path, "w", encoding="UTF-8") as logfile:
            if output_path.suffix == ".json" or not isinstance(content, str):
                json.dump(content or [], logfile, indent=4, sort_keys=True)
            else:
                logfile.write(content or "NO CONTENT")
