"""Access to a MyBMW account and all vehicles therein."""

import datetime
import json
import logging
from dataclasses import InitVar, dataclass, field
from typing import List, Optional

import httpx

from bimmer_connected.api.authentication import MyBMWAuthentication
from bimmer_connected.api.client import RESPONSE_STORE, MyBMWClient, MyBMWClientConfiguration
from bimmer_connected.api.regions import Regions
from bimmer_connected.const import (
    ATTR_CAPABILITIES,
    VEHICLE_CHARGING_DETAILS_URL,
    VEHICLE_STATE_URL,
    VEHICLES_URL,
    CarBrands,
)
from bimmer_connected.models import AnonymizedResponse, GPSPosition, MyBMWAPIError, MyBMWAuthError, MyBMWQuotaError
from bimmer_connected.vehicle import MyBMWVehicle

VALID_UNTIL_OFFSET = datetime.timedelta(seconds=10)

_LOGGER = logging.getLogger(__name__)


@dataclass
class MyBMWAccount:
    """Create a new connection to the MyBMW web service."""

    username: str
    """MyBMW user name (email) or 86-prefixed phone number (China only)."""

    password: InitVar[str]
    """MyBMW password."""

    region: Regions
    """Region of the account. See `api.Regions`."""

    config: MyBMWClientConfiguration = None  # type: ignore[assignment]
    """Optional. If provided, username/password/region are ignored."""

    log_responses: InitVar[bool] = False
    """Optional. If set, all responses from the server will be logged to this directory."""

    observer_position: InitVar[GPSPosition] = None
    """Optional. Required for getting a position on older cars."""

    use_metric_units: InitVar[Optional[bool]] = None
    """Deprecated. All returned values are metric units (km, l)."""

    vehicles: List[MyBMWVehicle] = field(default_factory=list, init=False)

    def __post_init__(self, password, log_responses, observer_position, use_metric_units):
        """Initialize the account."""

        if use_metric_units is not None:
            _LOGGER.warning(
                "The use_metric_units parameter is deprecated and will be removed in a future release. "
                "All values will be returned in metric units, as the parameter has no effect on the API."
            )

        if self.config is None:
            self.config = MyBMWClientConfiguration(
                MyBMWAuthentication(self.username, password, self.region),
                log_responses=log_responses,
                observer_position=observer_position,
            )

    async def _init_vehicles(self) -> None:
        """Initialize vehicles from BMW servers."""
        _LOGGER.debug("Getting vehicle list")

        fetched_at = datetime.datetime.now(datetime.timezone.utc)

        async with MyBMWClient(self.config) as client:
            vehicles_responses: List[httpx.Response] = [
                await client.get(
                    VEHICLES_URL,
                    headers={
                        **client.generate_default_header(brand),
                    },
                )
                for brand in CarBrands
            ]

            for response in vehicles_responses:
                for vehicle_base in response.json():
                    self.add_vehicle(vehicle_base, None, None, fetched_at)

    async def get_vehicles(self, force_init: bool = False) -> None:
        """Retrieve vehicle data from BMW servers."""
        _LOGGER.debug("Getting vehicle list")

        fetched_at = datetime.datetime.now(datetime.timezone.utc)

        if len(self.vehicles) == 0 or force_init:
            await self._init_vehicles()

        async with MyBMWClient(self.config) as client:
            error_count = 0
            for vehicle in self.vehicles:
                # Get the detailed vehicle state
                try:
                    state_response = await client.get(
                        VEHICLE_STATE_URL,
                        params={
                            "apptimezone": self.utcdiff,
                            "appDateTime": int(fetched_at.timestamp() * 1000),
                        },
                        headers={
                            **client.generate_default_header(vehicle.brand),
                            "bmw-vin": vehicle.vin,
                        },
                    )
                    vehicle_state = state_response.json()

                    # Get detailed charging settings if supported by vehicle
                    charging_settings = None
                    if vehicle_state[ATTR_CAPABILITIES].get("isChargingPlanSupported", False) or vehicle_state[
                        ATTR_CAPABILITIES
                    ].get("isChargingSettingsEnabled", False):
                        charging_settings_response = await client.get(
                            VEHICLE_CHARGING_DETAILS_URL,
                            params={
                                "fields": "charging-profile",
                                "has_charging_settings_capabilities": vehicle_state[ATTR_CAPABILITIES][
                                    "isChargingSettingsEnabled"
                                ],
                            },
                            headers={
                                **client.generate_default_header(vehicle.brand),
                                "bmw-current-date": fetched_at.isoformat(),
                                "bmw-vin": vehicle.vin,
                            },
                        )
                        charging_settings = charging_settings_response.json()

                    self.add_vehicle(vehicle.data, vehicle_state, charging_settings, fetched_at)
                except (MyBMWAPIError, json.JSONDecodeError) as ex:
                    # We don't want to fail completely if one vehicle fails, but we want to know about it
                    error_count += 1

                    # If it's a MyBMWQuotaError or MyBMWAuthError, we want to raise it
                    if isinstance(ex, (MyBMWQuotaError, MyBMWAuthError)):
                        raise ex

                    # Always log the error
                    _LOGGER.error("Unable to get details for vehicle %s - (%s) %s", vehicle.vin, type(ex).__name__, ex)

                    # If all vehicles fail, we want to raise an exception
                    if error_count == len(self.vehicles):
                        raise ex

    def add_vehicle(
        self,
        vehicle_base: dict,
        vehicle_state: Optional[dict],
        charging_settings: Optional[dict],
        fetched_at: Optional[datetime.datetime] = None,
    ) -> None:
        """Add or update a vehicle from the API responses."""

        existing_vehicle = self.get_vehicle(vehicle_base["vin"])

        # If vehicle already exists, just update it's state
        if existing_vehicle:
            existing_vehicle.update_state(vehicle_base, vehicle_state, charging_settings, fetched_at)
        else:
            self.vehicles.append(MyBMWVehicle(self, vehicle_base, vehicle_state, charging_settings, fetched_at))

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

    def set_refresh_token(self, refresh_token: str, gcid: Optional[str] = None) -> None:
        """Overwrite the current value of the MyBMW refresh token and GCID (if available)."""
        self.config.authentication.refresh_token = refresh_token
        self.config.authentication.gcid = gcid

    @staticmethod
    def get_stored_responses() -> List[AnonymizedResponse]:
        """Return responses stored if log_responses was set to True."""
        responses = list(RESPONSE_STORE)
        RESPONSE_STORE.clear()
        return responses

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

    @property
    def gcid(self) -> Optional[str]:
        """Returns the current GCID."""
        return self.config.authentication.gcid
