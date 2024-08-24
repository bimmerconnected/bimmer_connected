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
            return cls.UNKNOWN
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
        non_null_values = [k for k, v in self.__dict__.items() if v is None]
        if len(non_null_values) not in [0, len(self.__dataclass_fields__)]:
            raise TypeError(f"{type(self).__name__} requires either none or both arguments set")

        for field_name in self.__dataclass_fields__:
            value = getattr(self, field_name)
            if value is not None and not isinstance(value, (float, int)):
                raise TypeError(f"{type(self).__name__} '{field_name}' not of type '{Optional[Union[float, int]]}'")
            if field_name == "latitude" and not (-90 <= value <= 90):
                raise ValueError(f"{type(self).__name__}  'latitude' must be between -90 and 90, but got '{value}'")
            elif field_name == "longitude" and not (-180 <= value <= 180):
                raise ValueError(f"{type(self).__name__} 'longitude' must be between -180 and 180, but got '{value}'")
            # Force conversion to float
            setattr(self, field_name, float(value))

    @classmethod
    def init_nonempty(cls, latitude: Optional[float], longitude: Optional[float]):
        """Initialize GPSPosition but do not allow empty latitude/longitude."""
        if latitude is None or longitude is None:
            raise ValueError(f"{cls.__name__} requires both 'latitude' and 'longitude' set")
        return cls(latitude, longitude)

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
    formatted: Optional[str] = None

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
    subblock: Optional[str] = None


@dataclass
class PointOfInterest:
    """A Point of Interest to be sent to the car."""

    lat: InitVar[float]
    lon: InitVar[float]
    name: InitVar[Optional[str]] = DEFAULT_POI_NAME
    street: InitVar[str] = None
    postal_code: InitVar[str] = None
    city: InitVar[str] = None
    country: InitVar[str] = None

    position: Dict[str, float] = field(init=False)
    address: Optional[PointOfInterestAddress] = field(init=False)
    # The following attributes are not by us but required in the API
    formattedAddress: Optional[str] = None
    entrances: Optional[List] = field(init=False)
    placeType: Optional[str] = "ADDRESS"
    category: Dict[str, Optional[str]] = field(init=False)
    title: Optional[str] = DEFAULT_POI_NAME

    # The following attributes are not by us but available in the API
    provider: Optional[str] = None
    providerId: Optional[str] = None
    providerPoiId: str = ""
    sourceType: Optional[str] = None
    vehicleCategoryId: Optional[str] = None

    def __post_init__(self, lat, lon, name, street, postal_code, city, country):
        position = GPSPosition(lat, lon)
        self.position = {
            "lat": position.latitude,
            "lon": position.longitude,
        }

        self.address = PointOfInterestAddress(str(street), str(postal_code), str(city), str(country))
        self.category = {"losCategory": "Address", "mguVehicleCategoryId": None, "name": "Address"}
        self.title = name

        if not self.formattedAddress:
            self.formattedAddress = ", ".join([str(i) for i in [street, postal_code, city] if i]) or "Coordinates only"


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
