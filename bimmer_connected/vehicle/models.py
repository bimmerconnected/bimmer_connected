"""Generals models used for bimmer_connected."""

import logging
from dataclasses import InitVar, dataclass, field
from enum import Enum
from typing import Dict, NamedTuple, Optional, Union

_LOGGER = logging.getLogger(__name__)


class StrEnum(str, Enum):
    """A string enumeration of type `(str, Enum)`. All members are compared via `upper()`."""

    @classmethod
    def _missing_(cls, value):
        for member in cls:
            if member.value.upper() == value.upper():
                return member
        raise ValueError(f"'{value}' is not a valid {cls.__name__}")


@dataclass
class VehicleDataBase:
    """A base class for parsing and storing complex vehicle data."""

    @classmethod
    def from_vehicle_data(cls, vehicle_data: Dict):
        """Creates the class based on vehicle data from API."""
        parsed = cls._parse_vehicle_data(vehicle_data) or {}
        if len(parsed) > 0:
            return cls(**parsed)
        return None

    def update_from_vehicle_data(self, vehicle_data: Dict):
        """Updates the attributes based on vehicle data from API."""
        parsed = self._parse_vehicle_data(vehicle_data) or {}
        parsed.update(self._update_after_parse(parsed))
        if len(parsed) > 0:
            self.__dict__.update(parsed)

    @classmethod
    def _parse_vehicle_data(cls, vehicle_data: Dict) -> Dict:
        """Parses desired attributes out of vehicle data from API."""
        raise NotImplementedError()

    def _update_after_parse(self, parsed: Dict) -> Dict:
        """Updates parsed vehicle data with attributes stored in class if needed."""
        # pylint:disable=no-self-use
        return parsed


class Coordinates(NamedTuple):
    """Storage for GPS coordinates."""

    latitude: Optional[float]
    longitude: Optional[float]


class GPSPosition(Coordinates):
    """GPS coordinates."""

    __slots__ = ()  # Prevent creation of a __dict__.

    @classmethod
    def __new__(cls, *args, **kwargs):
        if len([a for a in args + tuple(kwargs.values()) if a is None]) not in [0, len(cls._fields)]:
            raise TypeError("Either none or all arguments must be 'None'.")
        annotations = cls.__annotations__  # pylint: disable=no-member
        for i, field_name in enumerate(annotations, 1):
            value = args[i] if (len(args) - 1) == i else kwargs.get(field_name)
            if value is not None and not isinstance(value, (float, int)):
                raise TypeError(f"'{field_name}' not of type '{Optional[Union[float, int]]}'")
        return super().__new__(*args, **kwargs)


@dataclass
class PointOfInterestAddress:
    """Address data of a PointOfInterest."""

    street: Optional[str] = None
    postalCode: Optional[str] = None  # pylint: disable=invalid-name
    city: Optional[str] = None
    country: Optional[str] = None


@dataclass
class PointOfInterest:
    """A Point of Interest to be sent to the car."""

    lat: InitVar[float]
    lon: InitVar[float]
    name: Optional[str] = None
    street: InitVar[str] = None
    postal_code: InitVar[str] = None
    city: InitVar[str] = None
    country: InitVar[str] = None

    coordinates: GPSPosition = field(init=False)
    locationAddress: Optional[PointOfInterestAddress] = field(init=False)  # pylint: disable=invalid-name
    type: str = field(default="SHARED_DESTINATION_FROM_EXTERNAL_APP", init=False)

    def __post_init__(self, lat, lon, street, postal_code, city, country):  # pylint: disable=too-many-arguments
        self.coordinates = GPSPosition(lat, lon)
        # pylint: disable=invalid-name
        self.locationAddress = PointOfInterestAddress(street, postal_code, city, country)


def check_strict_types(cls):
    """Checks a dataclass for strict typing. Use in __post_init__."""
    for field_name, field_def in cls.__dataclass_fields__.items():  # pylint: disable=no-member
        try:
            original_type = field_def.type.__args__
            field_type = original_type or field_def.type
        except AttributeError:
            field_type = field_def.type

        if not isinstance(getattr(cls, field_name), field_type):
            raise TypeError(f"'{field_name}' not of type '{field_def.type}'")


class ValueWithUnit(NamedTuple):
    """A value with a corresponding unit."""

    value: Union[int, float]
    unit: str
