"""Access to a MyBMW account and all vehicles therein."""

import datetime
import json
import logging
import pathlib
from dataclasses import InitVar, dataclass, field
from tempfile import TemporaryDirectory
from typing import Any, Dict, List, Optional

import httpx

from bimmer_connected.api.authentication import MyBMWAuthentication
from bimmer_connected.api.client import MyBMWClient, MyBMWClientConfiguration
from bimmer_connected.api.regions import Regions
from bimmer_connected.const import VEHICLE_STATE_URL, VEHICLES_URL, CarBrands
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

        fetched_at = datetime.datetime.now(datetime.timezone.utc)

        async with MyBMWClient(self.config) as client:
            vehicles_responses: List[httpx.Response] = [
                await client.get(
                    VEHICLES_URL,
                    headers={
                        **client.generate_default_header(brand),
                        "bmw-current-date": fetched_at.isoformat(),
                    },
                )
                for brand in CarBrands
            ]

            for response in vehicles_responses:
                for vehicle_base in response.json():
                    # Get the detailed vehicle state
                    state_response = await client.get(
                        VEHICLE_STATE_URL.format(vin=vehicle_base["vin"]),
                        headers=response.request.headers,  # Reuse the same headers as used to get vehicle list
                    )
                    vehicle_state = state_response.json()

                    self.add_vehicle(vehicle_base, vehicle_state, fetched_at)

    async def get_fingerprints(self) -> Dict[str, Any]:
        """Retrieve vehicle data from BMW servers and return original responses as JSON."""
        original_log_response_path = self.config.log_response_path
        fingerprints = {}

        try:
            # Use a temporary directory to just get the files from one call to get_vehicles()
            with TemporaryDirectory() as tempdir:
                tempdir_path = pathlib.Path(tempdir)
                self.config.log_response_path = tempdir_path
                await self.get_vehicles()
                for logfile in tempdir_path.iterdir():
                    with open(logfile, "rb") as pointer:
                        fingerprints[logfile.name] = json.load(pointer)
        finally:
            # Make sure that log_response_path is always set to the original value afterwards
            self.config.log_response_path = original_log_response_path

        return fingerprints

    def add_vehicle(self, vehicle_base: dict, vehicle_state: dict, fetched_at: datetime.datetime = None) -> None:
        """Add or update a vehicle from the API responses."""

        existing_vehicle = self.get_vehicle(vehicle_base["vin"])

        # If vehicle already exists, just update it's state
        if existing_vehicle:
            existing_vehicle.update_state(vehicle_base, vehicle_state, fetched_at)
        else:
            self.vehicles.append(MyBMWVehicle(self, vehicle_base, vehicle_state, fetched_at))

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
