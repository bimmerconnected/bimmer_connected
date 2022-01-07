"""Generals models used for bimmer_connected."""

from dataclasses import InitVar, dataclass, field
from typing import Optional


@dataclass
class GPSPosition:
    """A GPS Position."""

    latitude: float
    longitude: float
    altitude: Optional[float] = None
    direction: Optional[float] = None

    def __post_init__(self):
        check_strict_types(self)


@dataclass
class PointOfInterestCoordinates:
    """Coordinates of a PointOfInterest."""

    latitude: float
    longitude: float

    def __post_init__(self):
        check_strict_types(self)


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

    coordinates: PointOfInterestCoordinates = field(init=False)
    locationAddress: Optional[PointOfInterestAddress] = field(init=False)  # pylint: disable=invalid-name
    type: str = field(default="SHARED_DESTINATION_FROM_EXTERNAL_APP", init=False)

    def __post_init__(self, lat, lon, street, postal_code, city, country):  # pylint: disable=too-many-arguments
        self.coordinates = PointOfInterestCoordinates(lat, lon)
        # pylint: disable=invalid-name
        self.locationAddress = PointOfInterestAddress(street, postal_code, city, country)


def check_strict_types(cls):
    """Checks a dataclass for strict typing. Use in __post_init__."""
    for field_name, field_def in cls.__dataclass_fields__.items():  # pylint: disable=no-member
        try:
            original_type = field_def.type.__args__
            field_type = original_type or field_def.type  # pylint: disable=protected-access
        except AttributeError:
            field_type = field_def.type

        if not isinstance(getattr(cls, field_name), field_type):
            raise TypeError(f"'{field_name}' not of type '{field_def.type}'")
