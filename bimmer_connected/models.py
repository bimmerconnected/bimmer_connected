"""Generals models used for bimmer_connected."""

import logging
from dataclasses import InitVar, dataclass, field
from enum import Enum
from typing import Dict, NamedTuple, Optional, Tuple, Union

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
    def _parse_vehicle_data(cls, vehicle_data: Dict) -> Optional[Dict]:
        """Parses desired attributes out of vehicle data from API."""
        raise NotImplementedError()

    def _update_after_parse(self, parsed: Dict) -> Dict:
        """Updates parsed vehicle data with attributes stored in class if needed."""
        # pylint:disable=no-self-use
        return parsed


@dataclass
class GPSPosition:
    """GPS coordinates."""

    latitude: Optional[float]
    longitude: Optional[float]

    def __post_init__(self):
        # pylint: disable=no-member
        if len([v for v in self.__dict__.values() if v is None]) not in [0, len(self.__dataclass_fields__)]:
            raise TypeError("Either none or all arguments must be 'None'.")

        # pylint: disable=no-member
        for field_name in self.__dataclass_fields__:
            value = getattr(self, field_name)
            if value is not None and not isinstance(value, (float, int)):
                raise TypeError(f"'{field_name}' not of type '{Optional[Union[float, int]]}'")

    def __iter__(self):
        yield from self.__dict__.values()

    def __getitem__(self, key):
        return tuple(self.__dict__.values())[key]

    def __eq__(self, other):
        if isinstance(other, Tuple):
            return tuple(self.__iter__()) == other
        if hasattr(self, "__dict__") and hasattr(other, "__dict__"):
            return self.__dict__ == other.__dict__
        if hasattr(self, "__dict__") and isinstance(other, Dict):
            return self.__dict__ == other
        return False


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


class ValueWithUnit(NamedTuple):
    """A value with a corresponding unit."""

    value: Optional[Union[int, float]]
    unit: Optional[str]
