"""Trigger remote services on a vehicle."""

import asyncio
import datetime
import json
import logging
from typing import TYPE_CHECKING, Dict, Union

from bimmer_connected.api.client import MyBMWClient
from bimmer_connected.const import (
    REMOTE_SERVICE_POSITION_URL,
    REMOTE_SERVICE_STATUS_URL,
    REMOTE_SERVICE_URL,
    VEHICLE_POI_URL,
)
from bimmer_connected.utils import MyBMWJSONEncoder
from bimmer_connected.vehicle.models import PointOfInterest, StrEnum

if TYPE_CHECKING:
    from bimmer_connected.vehicle import MyBMWVehicle

TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"

_LOGGER = logging.getLogger(__name__)

#: time in seconds between polling updates on the status of a remote service
_POLLING_CYCLE = 3

#: maximum number of seconds to wait for the server to return a positive answer
_POLLING_TIMEOUT = 240


class ExecutionState(StrEnum):
    """Enumeration of possible states of the execution of a remote service."""

    INITIATED = "INITIATED"
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    EXECUTED = "EXECUTED"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"


class Services(StrEnum):
    """Enumeration of possible services to be executed."""

    LIGHT_FLASH = "light-flash"
    VEHICLE_FINDER = "vehicle-finder"
    DOOR_LOCK = "door-lock"
    DOOR_UNLOCK = "door-unlock"
    HORN = "horn-blow"
    AIR_CONDITIONING = "climate-now"
    CHARGE_NOW = "CHARGE_NOW"


class RemoteServiceStatus:  # pylint: disable=too-few-public-methods
    """Wraps the status of the execution of a remote service."""

    def __init__(self, response: dict):
        """Construct a new object from a dict."""
        status = None
        if "eventStatus" in response:
            status = response.get("eventStatus")

        self.state = ExecutionState(status or "UNKNOWN")
        self.details = response


class RemoteServices:
    """Trigger remote services on a vehicle."""

    def __init__(self, vehicle: "MyBMWVehicle"):
        """Constructor."""
        self._account = vehicle.account
        self._vehicle = vehicle

    async def trigger_remote_light_flash(self) -> RemoteServiceStatus:
        """Trigger the vehicle to flash its headlights.

        A state update is NOT triggered after this, as the vehicle state is unchanged.
        """
        _LOGGER.debug("Triggering remote light flash")
        return await self.trigger_remote_service(Services.LIGHT_FLASH)

    async def trigger_remote_door_lock(self) -> RemoteServiceStatus:
        """Trigger the vehicle to lock its doors.

        A state update is triggered after this, as the lock state of the vehicle changes.
        """
        _LOGGER.debug("Triggering remote door lock")
        result = await self.trigger_remote_service(Services.DOOR_LOCK)
        await self._trigger_state_update()
        return result

    async def trigger_remote_door_unlock(self) -> RemoteServiceStatus:
        """Trigger the vehicle to unlock its doors.

        A state update is triggered after this, as the lock state of the vehicle changes.
        """
        _LOGGER.debug("Triggering remote door unlock")
        result = await self.trigger_remote_service(Services.DOOR_UNLOCK)
        await self._trigger_state_update()
        return result

    async def trigger_remote_horn(self) -> RemoteServiceStatus:
        """Trigger the vehicle to sound its horn.

        A state update is NOT triggered after this, as the vehicle state is unchanged.
        """
        _LOGGER.debug("Triggering remote horn sound")
        return await self.trigger_remote_service(Services.HORN)

    async def trigger_charge_now(self) -> RemoteServiceStatus:
        """Trigger the vehicle to start charging.

        A state update is NOT triggered after this, as the vehicle state is unchanged.
        """
        _LOGGER.debug("Triggering charge now")
        result = await self.trigger_remote_service(Services.CHARGE_NOW)
        await self._trigger_state_update()
        return result

    async def trigger_remote_air_conditioning(self) -> RemoteServiceStatus:
        """Trigger the air conditioning to start.

        A state update is NOT triggered after this, as the vehicle state is unchanged.
        """
        _LOGGER.debug("Triggering remote air conditioning")
        result = await self.trigger_remote_service(Services.AIR_CONDITIONING, {"action": "START"})
        await self._trigger_state_update()
        return result

    async def trigger_remote_air_conditioning_stop(self) -> RemoteServiceStatus:
        """Trigger the air conditioning to stop.

        A state update is NOT triggered after this, as the vehicle state is unchanged.
        """
        _LOGGER.debug("Triggering remote air conditioning")
        result = await self.trigger_remote_service(Services.AIR_CONDITIONING, {"action": "STOP"})
        await self._trigger_state_update()
        return result

    async def trigger_remote_service(self, service_id: Services, params: Dict = None) -> RemoteServiceStatus:
        """Trigger a generic remote service and wait for the result."""
        event_id = await self._start_remote_service(service_id, params)
        status = await self._block_until_done(event_id)
        return status

    async def _start_remote_service(self, service_id: Services, params: Dict = None) -> str:
        """Start a generic remote service."""

        url = REMOTE_SERVICE_URL.format(vin=self._vehicle.vin, service_type=service_id.value)
        async with MyBMWClient(self._account.mybmw_client_config, brand=self._vehicle.brand) as client:
            response = await client.post(url, params=params)
        return response.json().get("eventId")

    async def _block_until_done(self, event_id: str) -> RemoteServiceStatus:
        """Keep polling the server until we get a final answer.

        :raises TimeoutError: if there is no final answer before _POLLING_TIMEOUT
        """
        fail_after = datetime.datetime.now() + datetime.timedelta(seconds=_POLLING_TIMEOUT)
        while datetime.datetime.now() < fail_after:
            await asyncio.sleep(_POLLING_CYCLE)
            status = await self._get_remote_service_status(event_id)
            _LOGGER.debug("current state of '%s' is: %s", event_id, status.state.value)
            if status.state == ExecutionState.ERROR:
                raise Exception(f"Remote service failed with state '{status.state}'. Response: {status.details}")
            if status.state not in [ExecutionState.UNKNOWN, ExecutionState.PENDING, ExecutionState.DELIVERED]:
                return status
        raise TimeoutError(
            f"Did not receive remote service result for '{event_id}' in {_POLLING_TIMEOUT} seconds. "
            f"Current state: {status.state.value}"
        )

    async def _get_remote_service_status(self, event_id: str = None) -> RemoteServiceStatus:
        """The execution status of the last remote service that was triggered."""
        _LOGGER.debug("getting remote service status for '%s'", event_id)
        url = REMOTE_SERVICE_STATUS_URL.format(vin=self._vehicle.vin, event_id=event_id)
        async with MyBMWClient(self._account.mybmw_client_config, brand=self._vehicle.brand) as client:
            response = await client.post(url)
        return RemoteServiceStatus(response.json())

    async def _trigger_state_update(self) -> None:
        """Sleep for 2x POLLING_CYCLE and force-refresh vehicles from BMW servers."""
        await asyncio.sleep(_POLLING_CYCLE * 2)
        await self._account.get_vehicles()

    async def trigger_send_poi(self, poi: Union[PointOfInterest, Dict]) -> RemoteServiceStatus:
        """Send a PointOfInterest to the vehicle.

        :param poi: A PointOfInterest containing at least 'lat' and 'lon' and optionally
            'name', 'street', 'city', 'postalCode', 'country'

        A state update is NOT triggered after this, as the vehicle state is unchanged.
        """
        _LOGGER.debug("Sending PointOfInterest to car")

        if isinstance(poi, Dict):
            poi = PointOfInterest(**poi)

        async with MyBMWClient(self._account.mybmw_client_config, brand=self._vehicle.brand) as client:
            await client.post(
                VEHICLE_POI_URL,
                headers={"content-type": "application/json"},
                content=json.dumps(
                    {
                        "location": poi.__dict__,
                        "vin": self._vehicle.vin,
                    },
                    cls=MyBMWJSONEncoder,
                ),
            )

        # send-to-car has no separate ExecutionStates
        return RemoteServiceStatus({"eventStatus": "EXECUTED"})

    async def trigger_remote_vehicle_finder(self) -> RemoteServiceStatus:
        """Trigger the vehicle finder.

        A state update is triggered after this, as the location state of the vehicle changes.
        """
        _LOGGER.debug("Triggering remote vehicle finder")
        event_id = await self._start_remote_service(Services.VEHICLE_FINDER)
        status = await self._block_until_done(event_id)
        result = await self._get_event_position(event_id)
        self._vehicle.vehicle_location.set_remote_service_position(result)
        return status

    async def _get_event_position(self, event_id) -> Dict:
        url = REMOTE_SERVICE_POSITION_URL.format(event_id=event_id)
        if not self._account.observer_position:
            return {
                "errorDetails": {
                    "title": "Unknown position",
                    "description": "Set observer position to retrieve vehicle coordinates!",
                }
            }
        async with MyBMWClient(self._account.mybmw_client_config, brand=self._vehicle.brand) as client:
            response = await client.post(
                url,
                headers={
                    "latitude": str(self._account.observer_position.latitude),
                    "longitude": str(self._account.observer_position.longitude),
                },
            )
        return response.json()
