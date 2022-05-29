"""Access to a MyBMW account and all vehicles therein."""

import datetime
import logging
import pathlib
from dataclasses import InitVar, dataclass, field
from typing import List, Optional

import httpx

from bimmer_connected.api.authentication import MyBMWAuthentication
from bimmer_connected.api.client import MyBMWClient, MyBMWClientConfiguration
from bimmer_connected.api.regions import Regions
from bimmer_connected.const import VEHICLES_URL, CarBrands
from bimmer_connected.models import GPSPosition
from bimmer_connected.utils import deprecated
from bimmer_connected.vehicle import MyBMWVehicle

VALID_UNTIL_OFFSET = datetime.timedelta(seconds=10)

_LOGGER = logging.getLogger(__name__)


@dataclass
class MyBMWAccount:  # pylint: disable=too-many-instance-attributes
    """Create a new connection to the MyBMW web service."""

    username: str
    """MyBMW user name (email) or 86-prefixed phone number (China only)."""

    password: InitVar[str]
    """MyBMW password."""

    region: Regions
    """Region of the account. See `api.Regions`."""

    config: MyBMWClientConfiguration = None  # type: ignore[assignment]
    """Optional. If provided, username/password/region are ignored."""

    log_responses: InitVar[pathlib.Path] = None
    """Optional. If set, all responses from the server will be logged to this directory."""

    observer_position: InitVar[GPSPosition] = None
    """Optional. Required for getting a position on older cars."""

    use_metric_units: InitVar[bool] = True
    """Optional. Use metric units (km, l) by default. Use imperial units (mi, gal) if False."""

    vehicles: List[MyBMWVehicle] = field(default_factory=list, init=False)

    def __post_init__(self, password, log_responses, observer_position, use_metric_units):
        if self.config is None:
            self.config = MyBMWClientConfiguration(
                MyBMWAuthentication(self.username, password, self.region),
                log_response_path=log_responses,
                observer_position=observer_position,
                use_metric_units=use_metric_units,
            )

    async def get_vehicles(self) -> None:
        """Retrieve vehicle data from BMW servers."""
        _LOGGER.debug("Getting vehicle list")

        async with MyBMWClient(self.config) as client:
            vehicles_request_params = {
                "apptimezone": self.utcdiff,
                "appDateTime": int(datetime.datetime.now().timestamp() * 1000),
                "tireGuardMode": "ENABLED",
            }
            vehicles_responses: List[httpx.Response] = [
                await client.get(
                    VEHICLES_URL,
                    params=vehicles_request_params,
                    headers=client.generate_default_header(brand),
                )
                for brand in CarBrands
            ]

            for response in vehicles_responses:
                for vehicle_dict in response.json():
                    # If vehicle already exists, just update it's state
                    existing_vehicle = self.get_vehicle(vehicle_dict["vin"])
                    if existing_vehicle:
                        existing_vehicle.update_state(vehicle_dict)
                    else:
                        self.vehicles.append(MyBMWVehicle(self, vehicle_dict))

    def get_vehicle(self, vin: str) -> Optional[MyBMWVehicle]:
        """Get vehicle with given VIN.

        The search is NOT case sensitive.
        :param vin: VIN of the vehicle you want to get.
        :return: Returns None if no vehicle is found.
        """
        for car in self.vehicles:
            if car.vin.upper() == vin.upper():
                return car
        return None

    def set_observer_position(self, latitude: float, longitude: float) -> None:
        """Set the position of the observer for all vehicles."""
        self.config.observer_position = GPSPosition(latitude=latitude, longitude=longitude)

    def set_refresh_token(self, refresh_token: str) -> None:
        """Overwrite the current value of the MyBMW refresh token."""
        self.config.authentication.refresh_token = refresh_token

    def set_use_metric_units(self, use_metric_units: bool) -> None:
        """Change between using metric units (km, l) if True or imperial units (mi, gal) if False."""
        self.config.use_metric_units = use_metric_units

    @property
    def timezone(self):
        """Returns the current tzinfo."""
        return datetime.datetime.now().astimezone().tzinfo

    @property
    def utcdiff(self):
        """Returns the difference to UTC in minutes."""
        return round(self.timezone.utcoffset(datetime.datetime.now()).seconds / 60, 0)

    @property
    def refresh_token(self) -> Optional[str]:
        """Returns the current refresh_token."""
        return self.config.authentication.refresh_token


@deprecated("MyBMWAccount")
class ConnectedDriveAccount(MyBMWAccount):
    """Deprecated class name for compatibility."""
