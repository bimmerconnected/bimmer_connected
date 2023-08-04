"""Generals models used for bimmer_connected."""

import logging
from dataclasses import InitVar, dataclass, field
from enum import Enum
from typing import Dict, List, NamedTuple, Optional, Tuple, Union

from bimmer_connected.const import DEFAULT_POI_NAME

_LOGGER = logging.getLogger(__name__)


class StrEnum(str, Enum):
    """A string enumeration of type `(str, Enum)`. All members are compared via `upper()`. Defaults to UNKNOWN."""

    @classmethod
    def _missing_(cls, value):
        has_unknown = False
        for member in cls:
            if member.value.upper() == "UNKNOWN":
                has_unknown = True
            if member.value.upper() == value.upper():
                return member
        if has_unknown:
            _LOGGER.warning("'%s' is not a valid '%s'", value, cls.__name__)
            return getattr(cls, "UNKNOWN")
        raise ValueError(f"'{value}' is not a valid {cls.__name__}")


@dataclass
class VehicleDataBase:
    """A base class for parsing and storing complex vehicle data."""

    @classmethod
    def from_vehicle_data(cls, vehicle_data: Dict):
        """Create the class based on vehicle data from API."""
        parsed = cls._parse_vehicle_data(vehicle_data) or {}
        if len(parsed) > 0:
            return cls(**parsed)
        return None

    def update_from_vehicle_data(self, vehicle_data: Dict):
        """Update the attributes based on vehicle data from API."""
        parsed = self._parse_vehicle_data(vehicle_data) or {}
        parsed.update(self._update_after_parse(parsed))
        if len(parsed) > 0:
            self.__dict__.update(parsed)

    @classmethod
    def _parse_vehicle_data(cls, vehicle_data: Dict) -> Optional[Dict]:
        """Parse desired attributes out of vehicle data from API."""
        raise NotImplementedError()

    def _update_after_parse(self, parsed: Dict) -> Dict:
        """Update parsed vehicle data with attributes stored in class if needed."""
        return parsed


@dataclass
class GPSPosition:
    """GPS coordinates."""

    latitude: Optional[float]
    longitude: Optional[float]

    def __post_init__(self):
        if len([v for v in self.__dict__.values() if v is None]) not in [0, len(self.__dataclass_fields__)]:
            raise TypeError("Either none or all arguments must be 'None'.")

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
    postalCode: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None

    # The following attributes are not by us but available in the API
    banchi: Optional[str] = None
    chome: Optional[str] = None
    countryCode: Optional[str] = None
    district: Optional[str] = None
    go: Optional[str] = None
    houseNumber: Optional[str] = None
    region: Optional[str] = None
    regionCode: Optional[str] = None
    settlement: Optional[str] = None


@dataclass
class PointOfInterest:
    """A Point of Interest to be sent to the car."""

    lat: InitVar[float]
    lon: InitVar[float]
    name: Optional[str] = DEFAULT_POI_NAME
    street: InitVar[str] = None
    postal_code: InitVar[str] = None
    city: InitVar[str] = None
    country: InitVar[str] = None

    coordinates: GPSPosition = field(init=False)
    locationAddress: Optional[PointOfInterestAddress] = field(init=False)
    # The following attributes are not by us but required in the API
    formattedAddress: Optional[str] = None
    entryPoints: List = field(init=False, default_factory=list)

    # The following attributes are not by us but available in the API
    address: Optional[str] = None
    baseCategoryId: Optional[str] = None
    phoneNumber: Optional[str] = None
    provider: Optional[str] = None
    providerId: Optional[str] = None
    providerPoiId: str = ""
    sourceType: Optional[str] = None
    type: Optional[str] = None
    vehicleCategoryId: Optional[str] = None

    def __post_init__(self, lat, lon, street, postal_code, city, country):
        self.coordinates = GPSPosition(lat, lon)

        self.locationAddress = PointOfInterestAddress(street, postal_code, city, country)

        if not self.formattedAddress:
            self.formattedAddress = ", ".join([i for i in [street, postal_code, city] if i]) or "Coordinates only"


class ValueWithUnit(NamedTuple):
    """A value with a corresponding unit."""

    value: Optional[Union[int, float]]
    unit: Optional[str]


@dataclass
class AnonymizedResponse:
    """An anonymized response."""

    filename: str
    content: Optional[Union[List, Dict, str]] = None


@dataclass
class ChargingSettings:
    """Charging settings to control the vehicle."""

    chargingTarget: Optional[int]
    isUnlockCableActive = None
    acLimitValue: Optional[int] = None
    dcLoudness = None


class MyBMWAPIError(Exception):
    """General BMW API error."""


class MyBMWAuthError(MyBMWAPIError):
    """Auth-related error from BMW API (HTTP status codes 401 and 403)."""


class MyBMWQuotaError(MyBMWAPIError):
    """Quota exceeded on BMW API."""


class MyBMWRemoteServiceError(MyBMWAPIError):
    """Error when executing remote services."""
