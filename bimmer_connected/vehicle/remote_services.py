"""Trigger remote services on a vehicle."""

import asyncio
import datetime
import json
import logging
from typing import TYPE_CHECKING, Any, Dict, Optional, Union

from bimmer_connected.api.client import MyBMWClient
from bimmer_connected.const import (
    REMOTE_SERVICE_POSITION_URL,
    REMOTE_SERVICE_STATUS_URL,
    REMOTE_SERVICE_URL,
    VEHICLE_CHARGING_PROFILE_SET_URL,
    VEHICLE_CHARGING_SETTINGS_SET_URL,
    VEHICLE_CHARGING_START_STOP_URL,
    VEHICLE_POI_URL,
)
from bimmer_connected.models import ChargingSettings, MyBMWRemoteServiceError, PointOfInterest, StrEnum
from bimmer_connected.utils import MyBMWJSONEncoder
from bimmer_connected.vehicle.charging_profile import (
    MAP_CHARGING_MODE_TO_REMOTE_SERVICE,
    ChargingMode,
    ChargingPreferences,
)
from bimmer_connected.vehicle.fuel_and_battery import ChargingState

if TYPE_CHECKING:
    from bimmer_connected.vehicle import MyBMWVehicle

TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"

_LOGGER = logging.getLogger(__name__)

#: time in seconds between polling updates on the status of a remote service
_POLLING_CYCLE = 3.5

#: maximum number of seconds to wait for the server to return a positive answer
_POLLING_TIMEOUT = 240


class ExecutionState(StrEnum):
    """Enumeration of possible states of the execution of a remote service."""

    INITIATED = "INITIATED"
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    EXECUTED = "EXECUTED"
    ERROR = "ERROR"
    IGNORED = "IGNORED"
    UNKNOWN = "UNKNOWN"


class Services(StrEnum):
    """Enumeration of possible services to be executed."""

    LIGHT_FLASH = "light-flash"
    VEHICLE_FINDER = "vehicle-finder"
    DOOR_LOCK = "door-lock"
    DOOR_UNLOCK = "door-unlock"
    HORN = "horn-blow"
    AIR_CONDITIONING = "climate-now"
    CHARGE_START = "start-charging"
    CHARGE_STOP = "stop-charging"
    CHARGING_SETTINGS = "CHARGING_SETTINGS"
    CHARGING_PROFILE = "CHARGING_PROFILE"
    SEND_POI = "SEND_POI"


# Non-default remote services URLs
SERVICE_URLS = {
    Services.CHARGING_SETTINGS: VEHICLE_CHARGING_SETTINGS_SET_URL,
    Services.CHARGING_PROFILE: VEHICLE_CHARGING_PROFILE_SET_URL,
    Services.SEND_POI: VEHICLE_POI_URL,
    Services.CHARGE_START: VEHICLE_CHARGING_START_STOP_URL,
    Services.CHARGE_STOP: VEHICLE_CHARGING_START_STOP_URL,
}

CHARGING_MODE_TO_CHARGING_PREFERENCE = {
    ChargingMode.IMMEDIATE_CHARGING: ChargingPreferences.NO_PRESELECTION,
    ChargingMode.DELAYED_CHARGING: ChargingPreferences.CHARGING_WINDOW,
}


class RemoteServiceStatus:
    """Wraps the status of the execution of a remote service."""

    def __init__(self, response: dict, event_id: Optional[str] = None):
        """Construct a new object from a dict."""
        status = None
        if "eventStatus" in response:
            status = response.get("eventStatus")

        self.state = ExecutionState(status or "UNKNOWN")
        self.details = response
        self.event_id = event_id


class RemoteServices:
    """Trigger remote services on a vehicle."""

    def __init__(self, vehicle: "MyBMWVehicle"):
        self._account = vehicle.account
        self._vehicle = vehicle

    async def trigger_remote_service(
        self, service_id: Services, params: Optional[Dict] = None, data: Any = None, refresh: bool = False
    ) -> RemoteServiceStatus:
        """Trigger a remote service and wait for the result."""

        # Check if service requires a specific url and add all required parameters
        url = SERVICE_URLS.get(service_id, REMOTE_SERVICE_URL)

        remote_service_headers = {"content-type": "application/json"}
        if "{vin}" not in url:
            remote_service_headers["bmw-vin"] = self._vehicle.vin

        url = url.format(vin=self._vehicle.vin, service_type=service_id.value, gcid=self._account.gcid)

        # Trigger service and get event id
        async with MyBMWClient(self._account.config, brand=self._vehicle.brand) as client:
            response = await client.post(
                url,
                headers=remote_service_headers,
                params=params,
                content=json.dumps(data or {}, cls=MyBMWJSONEncoder),
            )
            event_id = response.json().get("eventId") if response.content else None

            # Get status via event_id or assume successful execution as HTTP errors would raise exceptions before
            status = (
                await self._block_until_done(client, event_id)
                if event_id
                else RemoteServiceStatus({"eventStatus": "EXECUTED"})
            )

        # If vehicle data needs to be refresh, wait 2 times polling cycle and refresh completely
        if refresh:
            await asyncio.sleep(_POLLING_CYCLE * 2)
            await self._account.get_vehicles()

        return status

    async def _get_remote_service_status(self, client: MyBMWClient, event_id: str) -> RemoteServiceStatus:
        """Return execution status of the last remote service that was triggered."""

        _LOGGER.debug("getting remote service status for '%s'", event_id)
        url = REMOTE_SERVICE_STATUS_URL.format(vin=self._vehicle.vin, event_id=event_id)
        async with MyBMWClient(self._account.config, brand=self._vehicle.brand) as client:
            response = await client.post(url)
        return RemoteServiceStatus(response.json(), event_id=event_id)

    async def _block_until_done(self, client: MyBMWClient, event_id: str) -> RemoteServiceStatus:
        """Keep polling the server until we get a final answer.

        :raises TimeoutError: if there is no final answer before _POLLING_TIMEOUT
        """

        fail_after = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=_POLLING_TIMEOUT)
        while datetime.datetime.now(datetime.timezone.utc) < fail_after:
            await asyncio.sleep(_POLLING_CYCLE)
            status = await self._get_remote_service_status(client, event_id)
            _LOGGER.debug("current state of '%s' is: %s", event_id, status.state.value)
            if status.state == ExecutionState.ERROR:
                raise MyBMWRemoteServiceError(
                    f"Remote service failed with state '{status.state}'. Response: {status.details}"
                )
            if status.state not in [ExecutionState.UNKNOWN, ExecutionState.PENDING, ExecutionState.DELIVERED]:
                return status
        raise MyBMWRemoteServiceError(
            f"Did not receive remote service result for '{event_id}' in {_POLLING_TIMEOUT} seconds. "
            f"Current state: {status.state.value}"
        )

    async def trigger_remote_light_flash(self) -> RemoteServiceStatus:
        """Trigger the vehicle to flash its headlights."""
        if not self._vehicle.is_remote_lights_enabled:
            raise ValueError(f"Vehicle does not support remote service '{Services.LIGHT_FLASH.value}'.")
        return await self.trigger_remote_service(Services.LIGHT_FLASH)

    async def trigger_remote_door_lock(self) -> RemoteServiceStatus:
        """Trigger the vehicle to lock its doors."""
        if not self._vehicle.is_remote_lock_enabled:
            raise ValueError(f"Vehicle does not support remote service '{Services.DOOR_LOCK.value}'.")
        return await self.trigger_remote_service(Services.DOOR_LOCK, refresh=True)

    async def trigger_remote_door_unlock(self) -> RemoteServiceStatus:
        """Trigger the vehicle to unlock its doors."""
        if not self._vehicle.is_remote_unlock_enabled:
            raise ValueError(f"Vehicle does not support remote service '{Services.DOOR_UNLOCK.value}'.")
        return await self.trigger_remote_service(Services.DOOR_UNLOCK, refresh=True)

    async def trigger_remote_horn(self) -> RemoteServiceStatus:
        """Trigger the vehicle to sound its horn."""
        if not self._vehicle.is_remote_horn_enabled:
            raise ValueError(f"Vehicle does not support remote service '{Services.HORN.value}'.")
        return await self.trigger_remote_service(Services.HORN)

    async def trigger_charge_start(self) -> RemoteServiceStatus:
        """Trigger the vehicle to start charging."""
        if not self._vehicle.is_remote_charge_start_enabled:
            raise ValueError(f"Vehicle does not support remote service '{Services.CHARGE_START.value}'.")

        if not self._vehicle.fuel_and_battery.is_charger_connected:
            _LOGGER.warning("Charger not connected, cannot start charging.")
            return RemoteServiceStatus({"eventStatus": "IGNORED"})

        return await self.trigger_remote_service(Services.CHARGE_START, refresh=True)

    async def trigger_charge_stop(self) -> RemoteServiceStatus:
        """Trigger the vehicle to stop charging."""
        if not self._vehicle.is_remote_charge_stop_enabled:
            raise ValueError(f"Vehicle does not support remote service '{Services.CHARGE_STOP.value}'.")

        if not self._vehicle.fuel_and_battery.is_charger_connected:
            _LOGGER.warning("Charger not connected, cannot stop charging.")
            return RemoteServiceStatus({"eventStatus": "IGNORED"})
        if self._vehicle.fuel_and_battery.charging_status != ChargingState.CHARGING:
            _LOGGER.warning("Vehicle not charging, cannot stop charging.")
            return RemoteServiceStatus({"eventStatus": "IGNORED"})

        return await self.trigger_remote_service(Services.CHARGE_STOP, refresh=True)

    async def trigger_remote_air_conditioning(self) -> RemoteServiceStatus:
        """Trigger the air conditioning to start."""
        if not self._vehicle.is_remote_climate_start_enabled:
            raise ValueError(
                f"Vehicle does not support remote service '{Services.AIR_CONDITIONING.value}' action 'START'."
            )
        return await self.trigger_remote_service(Services.AIR_CONDITIONING, params={"action": "START"}, refresh=True)

    async def trigger_remote_air_conditioning_stop(self) -> RemoteServiceStatus:
        """Trigger the air conditioning to stop."""
        if not self._vehicle.is_remote_climate_stop_enabled:
            raise ValueError(
                f"Vehicle does not support remote service '{Services.AIR_CONDITIONING.value}' action 'STOP'."
            )
        return await self.trigger_remote_service(Services.AIR_CONDITIONING, params={"action": "STOP"}, refresh=True)

    async def trigger_charging_settings_update(
        self, target_soc: Optional[int] = None, ac_limit: Optional[int] = None
    ) -> RemoteServiceStatus:
        """Update the charging settings on the vehicle."""

        if target_soc and not self._vehicle.is_remote_set_target_soc_enabled:
            raise ValueError("Vehicle does not support setting target SoC.")
        if target_soc and (
            not isinstance(target_soc, int) or target_soc < 20 or target_soc > 100 or target_soc % 5 != 0
        ):
            raise ValueError("Target SoC must be an integer between 20 and 100 that is a multiple of 5.")
        if ac_limit:
            if (
                not self._vehicle.is_remote_set_ac_limit_enabled
                or not self._vehicle.charging_profile
                or not self._vehicle.charging_profile.ac_available_limits
            ):
                raise ValueError("Vehicle does not support setting AC Limit.")
            if not isinstance(ac_limit, int) or ac_limit not in self._vehicle.charging_profile.ac_available_limits:
                raise ValueError("AC Limit must be an integer and in `charging_profile.ac_available_limits`.")

        return await self.trigger_remote_service(
            Services.CHARGING_SETTINGS,
            data=ChargingSettings(chargingTarget=target_soc, acLimitValue=ac_limit),
            refresh=True,
        )

    async def trigger_charging_profile_update(
        self, charging_mode: Optional[ChargingMode] = None, precondition_climate: Optional[bool] = None
    ) -> RemoteServiceStatus:
        """Update the charging profile on the vehicle."""

        if not self._vehicle.is_charging_plan_supported or not self._vehicle.charging_profile:
            raise ValueError("Vehicle does not support setting charging profile.")

        target_charging_profile = self._vehicle.charging_profile.format_for_remote_service()

        if charging_mode and charging_mode != ChargingMode.UNKNOWN:
            target_charging_profile["chargingMode"]["type"] = MAP_CHARGING_MODE_TO_REMOTE_SERVICE[charging_mode]
            target_charging_profile["chargingMode"]["chargingPreference"] = CHARGING_MODE_TO_CHARGING_PREFERENCE[
                charging_mode
            ].value

        if precondition_climate is not None:
            target_charging_profile["isPreconditionForDepartureActive"] = precondition_climate

        return await self.trigger_remote_service(
            Services.CHARGING_PROFILE,
            data=target_charging_profile,
            refresh=True,
        )

    async def trigger_send_poi(self, poi: Union[PointOfInterest, Dict]) -> RemoteServiceStatus:
        """Send a PointOfInterest to the vehicle.

        :param poi: A PointOfInterest containing at least 'lat' and 'lon' and optionally
            'name', 'street', 'city', 'postalCode', 'country'
        """
        if not self._vehicle.is_remote_sendpoi_enabled:
            raise ValueError(f"Vehicle does not support remote service '{Services.SEND_POI.value}'.")

        if isinstance(poi, Dict):
            poi = PointOfInterest(**poi)

        return await self.trigger_remote_service(
            Services.SEND_POI,
            data={
                "places": [poi],
                "vehicleInformation": {
                    "vin": self._vehicle.vin,
                },
            },
        )

    async def trigger_remote_vehicle_finder(self) -> RemoteServiceStatus:
        """Trigger the vehicle finder."""
        # Even if the API reports this as False, calling the service still works
        # if not self._vehicle.is_vehicle_tracking_enabled:
        #     raise ValueError(f"Vehicle does not support remote service '{Services.VEHICLE_FINDER.value}'.")

        status = await self.trigger_remote_service(Services.VEHICLE_FINDER)
        result = await self._get_event_position(status.event_id)
        self._vehicle.vehicle_location.set_remote_service_position(result)
        return status

    async def _get_event_position(self, event_id) -> Dict:
        url = REMOTE_SERVICE_POSITION_URL.format(event_id=event_id)
        if not self._account.config.observer_position:
            return {
                "errorDetails": {
                    "title": "Unknown position",
                    "description": "Set observer position to retrieve vehicle coordinates!",
                }
            }
        async with MyBMWClient(self._account.config, brand=self._vehicle.brand) as client:
            response = await client.post(
                url,
                headers={
                    "latitude": str(self._account.config.observer_position.latitude),
                    "longitude": str(self._account.config.observer_position.longitude),
                },
            )
        return response.json()
