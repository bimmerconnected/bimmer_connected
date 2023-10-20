"""Access to a MyBMW account and all vehicles therein."""

import datetime
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
    VEHICLE_CHARGING_SESSIONS_URL,
    VEHICLE_CHARGING_STATISTICS_URL,
    VEHICLE_STATE_URL,
    VEHICLES_URL,
    CarBrands,
)
from bimmer_connected.models import AnonymizedResponse, GPSPosition
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

    use_metric_units: InitVar[bool] = True
    """Optional. Use metric units (km, l) by default. Use imperial units (mi, gal) if False."""

    vehicles: List[MyBMWVehicle] = field(default_factory=list, init=False)

    def __post_init__(self, password, log_responses, observer_position, use_metric_units):
        if self.config is None:
            self.config = MyBMWClientConfiguration(
                MyBMWAuthentication(self.username, password, self.region),
                log_responses=log_responses,
                observer_position=observer_position,
                use_metric_units=use_metric_units,
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
                    self.add_vehicle(vehicle_base, None, None, None, None, fetched_at)

    async def get_vehicles(self, force_init: bool = False) -> None:
        """Retrieve vehicle data from BMW servers."""
        _LOGGER.debug("Getting vehicle list")

        fetched_at = datetime.datetime.now(datetime.timezone.utc)

        if len(self.vehicles) == 0 or force_init:
            await self._init_vehicles()

        async with MyBMWClient(self.config) as client:
            for vehicle in self.vehicles:
                # Get the detailed vehicle state
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

                # Get detailed charging settings, charging-sessions and charging-statistics if supported by vehicle
                charging_settings = None
                charging_statistics = None
                charging_sessions = None

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

                    # Get all charging statistics for date range
                    charging_statistics_response = await client.get(
                        VEHICLE_CHARGING_STATISTICS_URL,
                        params={
                            "vin": vehicle.vin,
                            "currentDate": datetime.datetime.utcnow().isoformat(),
                        },
                        headers={
                            **client.generate_default_header(vehicle.brand),
                            "bmw-vin": vehicle.vin,
                        },
                    )
                    charging_statistics = charging_statistics_response.json()

                    # Get all charging sessions for date range
                    charging_sessions_response = await client.get(
                        VEHICLE_CHARGING_SESSIONS_URL,
                        params={
                            "vin": vehicle.vin,
                            # TODO: This yields the full date range with data: "include_date_picker": "true",
                            # "2023-04-01T00:00:00Z", Setting this will give session data for that month
                            "date": datetime.datetime.utcnow().isoformat(),
                        },
                        headers={
                            **client.generate_default_header(vehicle.brand),
                            "bmw-vin": vehicle.vin,
                        },
                    )
                    charging_sessions = charging_sessions_response.json()

                    async def get_charging_session(id: str):
                        """Get single charging session by ID.

                        :param id: the charging session ID
                        :return: Charging session details
                        """
                        charging_session_response = await client.get(
                            VEHICLE_CHARGING_SESSIONS_URL + f"/{id}",
                            params={
                                "vin": vehicle.vin,
                            },
                            headers={
                                **client.generate_default_header(vehicle.brand),
                                "bmw-vin": vehicle.vin,
                            },
                        )

                        charging_session_detail = charging_session_response.json()

                        return charging_session_detail

                    # Extend charging session with collected details if any
                    for charging_session in charging_sessions.get("chargingSessions", {}).get("sessions", []):
                        charging_session["details"] = await get_charging_session(charging_session.get("id"))

                self.add_vehicle(
                    vehicle.data, vehicle_state, charging_settings, charging_statistics, charging_sessions, fetched_at
                )

    def add_vehicle(
        self,
        vehicle_base: dict,
        vehicle_state: Optional[dict],
        charging_settings: Optional[dict],
        charging_statistics: Optional[dict],
        charging_sessions: Optional[dict],
        fetched_at: Optional[datetime.datetime] = None,
    ) -> None:
        """Add or update a vehicle from the API responses."""

        existing_vehicle = self.get_vehicle(vehicle_base["vin"])

        # If vehicle already exists, just update it's state
        if existing_vehicle:
            existing_vehicle.update_state(
                vehicle_base, vehicle_state, charging_settings, charging_statistics, charging_sessions, fetched_at
            )
        else:
            self.vehicles.append(
                MyBMWVehicle(
                    self,
                    vehicle_base,
                    vehicle_state,
                    charging_settings,
                    charging_statistics,
                    charging_sessions,
                    fetched_at,
                )
            )

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

    def set_use_metric_units(self, use_metric_units: bool) -> None:
        """Change between using metric units (km, l) if True or imperial units (mi, gal) if False."""
        self.config.use_metric_units = use_metric_units

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
