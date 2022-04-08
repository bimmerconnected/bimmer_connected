"""General utils and base classes used in the library."""

import base64
import datetime
import hashlib
import inspect
import json
import logging
import random
import string
import sys
from abc import ABC
from collections import OrderedDict

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_LOGGER = logging.getLogger(__name__)

UNICODE_CHARACTER_SET = string.ascii_letters + string.digits + '-._~'


def generate_token(length=30, chars=UNICODE_CHARACTER_SET):
    """Generate a random token with given length and characters."""
    rand = random.SystemRandom()
    return ''.join(rand.choice(chars) for _ in range(length))


def create_s256_code_challenge(code_verifier):
    """Create S256 code_challenge with the given code_verifier."""
    data = hashlib.sha256(code_verifier.encode('ascii')).digest()
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('UTF-8')


class RetrySession(requests.Session):
    """A `requests.Session` with `Retry`."""

    def __init__(
        self,
        retries=3,
        backoff_factor=0.3,
        status_forcelist=None,
        allowed_methods=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            allowed_methods=allowed_methods,
        )
        self.adapters = OrderedDict()
        self.mount('http://', HTTPAdapter(max_retries=retry))
        self.mount('https://', HTTPAdapter(max_retries=retry))


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
        if hasattr(obj, 'as_dict'):
            return getattr(obj, "as_dict")()
        if hasattr(obj, '__dict__'):
            return {k: v for k, v in getattr(obj, "__dict__").items() if not k.startswith("_")}
        return str(obj)

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

    def as_dict(self) -> dict:
        """Return all attributes and parameters."""
        return serialize_for_json(self)
