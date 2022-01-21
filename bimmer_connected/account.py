"""Library to read data from the BMW Connected Drive portal.

The library bimmer_connected provides a Python interface to interact
with the BMW Connected Drive web service. It allows you to read
the current state of the vehicle and also trigger remote services.

Disclaimer:
This library is not affiliated with or endorsed by BMW Group.
"""

import asyncio
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
from bimmer_connected.vehicle.models import GPSPosition
from bimmer_connected.vehicle import ConnectedDriveVehicle

VALID_UNTIL_OFFSET = datetime.timedelta(seconds=10)

_LOGGER = logging.getLogger(__name__)
# lock = asyncio.Lock()


@dataclass
class ConnectedDriveAccount:  # pylint: disable=too-many-instance-attributes
    """Create a new connection to the BMW Connected Drive web service.

    :param username: Connected drive user name
    :param password: Connected drive password
    :param region: Region for which the account was created. See `const.Regions`.
    :param mybmw_client: Optional. If given, username/password/region are ignored.
    :param log_responses: Optional. If set, all responses from the server will be logged to this directory.
    :param observer_position: Optional. Required for getting a position on older cars.
    """

    username: str
    password: InitVar[str]
    region: Regions

    mybmw_client_config: MyBMWClientConfiguration = None  # type: ignore[assignment]
    log_responses: InitVar[pathlib.Path] = None
    vehicles: List[ConnectedDriveVehicle] = field(default_factory=list, init=False)

    observer_position: Optional[GPSPosition] = None

    def __post_init__(self, password, log_responses):
        if self.mybmw_client_config is None:
            self.mybmw_client_config = MyBMWClientConfiguration(
                MyBMWAuthentication(self.username, password, self.region),
                log_response_path=log_responses,
            )

    async def get_vehicles(self) -> None:
        """Retrieve vehicle data from BMW servers."""
        _LOGGER.debug("Getting vehicle list")

        async with MyBMWClient(self.mybmw_client_config) as client:
            vehicles_request_params = {
                "apptimezone": self.utcdiff,
                "appDateTime": int(datetime.datetime.now().timestamp() * 1000),
                "tireGuardMode": "ENABLED",
            }
            vehicles_tasks: List[asyncio.Task] = []
            for brand in CarBrands:
                vehicles_tasks.append(
                    asyncio.ensure_future(
                        client.get(
                            VEHICLES_URL,
                            params=vehicles_request_params,
                            headers=client.generate_default_header(brand),
                        )
                    )
                )
            vehicles_responses: List[httpx.Response] = await asyncio.gather(*vehicles_tasks)

            for response in vehicles_responses:
                for vehicle_dict in response.json():
                    # If vehicle already exists, just update it's state
                    existing_vehicle = self.get_vehicle(vehicle_dict["vin"])
                    if existing_vehicle:
                        existing_vehicle.update_state(vehicle_dict)
                    else:
                        self.vehicles.append(ConnectedDriveVehicle(self, vehicle_dict))

    def get_vehicle(self, vin: str) -> Optional[ConnectedDriveVehicle]:
        """Get vehicle with given VIN.

        The search is NOT case sensitive.
        :param vin: VIN of the vehicle you want to get.
        :return: Returns None if no such vehicle is found.
        """
        for car in self.vehicles:
            if car.vin.upper() == vin.upper():
                return car
        return None

    def set_observer_position(self, latitude: float, longitude: float) -> None:
        """Set the position of the observer for all vehicles."""
        self.observer_position = GPSPosition(latitude=latitude, longitude=longitude)

    @property
    def timezone(self):
        """Returns the current tzinfo."""
        return datetime.datetime.now().astimezone().tzinfo

    @property
    def utcdiff(self):
        """Returns the difference to UTC in minutes."""
        return round(self.timezone.utcoffset(datetime.datetime.now()).seconds / 60, 0)
