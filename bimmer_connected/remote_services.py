"""Trigger remote services on a vehicle."""

import datetime
import json
from json.decoder import JSONDecodeError
import logging
import time
from typing import TYPE_CHECKING, Dict
from enum import Enum

from bimmer_connected.const import (REMOTE_SERVICE_POSITION_URL,
                                    REMOTE_SERVICE_STATUS_URL,
                                    REMOTE_SERVICE_URL,
                                    VEHICLE_POI_URL)

if TYPE_CHECKING:
    from bimmer_connected.account import ConnectedDriveAccount
    from bimmer_connected.vehicle import ConnectedDriveVehicle

TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'

_LOGGER = logging.getLogger(__name__)

#: time in seconds between polling updates on the status of a remote service
_POLLING_CYCLE = 3

#: maximum number of seconds to wait for the server to return a positive answer
_POLLING_TIMEOUT = 240

#: time in seconds to wait before updating the vehicle state from the server
_UPDATE_AFTER_REMOTE_SERVICE_DELAY = 10


class ExecutionState(str, Enum):
    """Enumeration of possible states of the execution of a remote service."""
    INITIATED = 'INITIATED'
    PENDING = 'PENDING'
    DELIVERED = 'DELIVERED'
    EXECUTED = 'EXECUTED'
    UNKNOWN = 'UNKNOWN'


class _Services(str, Enum):
    """Enumeration of possible services to be executed."""
    REMOTE_LIGHT_FLASH = 'LIGHT_FLASH'
    REMOTE_VEHICLE_FINDER = 'VEHICLE_FINDER'
    REMOTE_DOOR_LOCK = 'DOOR_LOCK'
    REMOTE_DOOR_UNLOCK = 'DOOR_UNLOCK'
    REMOTE_HORN = 'HORN_BLOW'
    REMOTE_AIR_CONDITIONING = 'CLIMATE_NOW'


class RemoteServiceStatus:  # pylint: disable=too-few-public-methods
    """Wraps the status of the execution of a remote service."""

    def __init__(self, response: dict):
        """Construct a new object from a dict."""
        status = None
        if 'executionStatus' in response:
            status = response["executionStatus"].get('status')
        elif 'eventStatus' in response:
            status = response.get("eventStatus")

        self.state = ExecutionState(status or 'UNKNOWN')


class RemoteServices:
    """Trigger remote services on a vehicle."""

    def __init__(self, account: "ConnectedDriveAccount", vehicle: "ConnectedDriveVehicle"):
        """Constructor."""
        self._account = account
        self._vehicle = vehicle

    def _get_event_position(self, event_id) -> Dict:
        url = REMOTE_SERVICE_POSITION_URL.format(
            server=self._account.server_url,
            event_id=event_id)
        if self._vehicle.observer_latitude is None or self._vehicle.observer_longitude is None:
            return {
                "errorDetails": {
                    "title": "Unkown position",
                    "description": "Set observer position to retrieve vehicle coordinates!"
                }
            }
        response = self._account.send_request(
            url,
            post=True,
            brand=self._vehicle.brand,
            headers={
                "latitude": str(self._vehicle.observer_latitude),
                "longitude": str(self._vehicle.observer_longitude)
            }
        )
        return response.json()

    def trigger_remote_light_flash(self) -> RemoteServiceStatus:
        """Trigger the vehicle to flash its headlights.

        A state update is NOT triggered after this, as the vehicle state is unchanged.
        """
        _LOGGER.debug('Triggering remote light flash')
        event_id = self._trigger_remote_service(_Services.REMOTE_LIGHT_FLASH)
        return self._block_until_done(_Services.REMOTE_LIGHT_FLASH, event_id)

    def trigger_remote_door_lock(self) -> RemoteServiceStatus:
        """Trigger the vehicle to lock its doors.

        A state update is triggered after this, as the lock state of the vehicle changes.
        """
        _LOGGER.debug('Triggering remote door lock')
        event_id = self._trigger_remote_service(_Services.REMOTE_DOOR_LOCK)
        result = self._block_until_done(_Services.REMOTE_DOOR_LOCK, event_id)
        self._trigger_state_update()
        return result

    def trigger_remote_door_unlock(self) -> RemoteServiceStatus:
        """Trigger the vehicle to unlock its doors.

        A state update is triggered after this, as the lock state of the vehicle changes.
        """
        _LOGGER.debug('Triggering remote door unlock')
        event_id = self._trigger_remote_service(_Services.REMOTE_DOOR_UNLOCK)
        result = self._block_until_done(_Services.REMOTE_DOOR_UNLOCK, event_id)
        self._trigger_state_update()
        return result

    def trigger_remote_horn(self) -> RemoteServiceStatus:
        """Trigger the vehicle to sound its horn.

        A state update is NOT triggered after this, as the vehicle state is unchanged.
        """
        _LOGGER.debug('Triggering remote horn sound')
        event_id = self._trigger_remote_service(_Services.REMOTE_HORN)
        return self._block_until_done(_Services.REMOTE_HORN, event_id)

    def trigger_remote_air_conditioning(self) -> RemoteServiceStatus:
        """Trigger the air conditioning to start.

        A state update is NOT triggered after this, as the vehicle state is unchanged.
        """
        _LOGGER.debug('Triggering remote air conditioning')
        event_id = self._trigger_remote_service(_Services.REMOTE_AIR_CONDITIONING, action="START")
        result = self._block_until_done(_Services.REMOTE_AIR_CONDITIONING, event_id)
        self._trigger_state_update()
        return result

    def trigger_remote_air_conditioning_stop(self) -> RemoteServiceStatus:
        """Trigger the air conditioning to stop.

        A state update is NOT triggered after this, as the vehicle state is unchanged.
        """
        _LOGGER.debug('Triggering remote air conditioning')
        event_id = self._trigger_remote_service(_Services.REMOTE_AIR_CONDITIONING, action="STOP")
        result = self._block_until_done(_Services.REMOTE_AIR_CONDITIONING, event_id)
        self._trigger_state_update()
        return result

    def _trigger_remote_service(self, service_id: _Services, action=None, post=True) -> str:
        """Trigger a generic remote service.

        You can choose if you want a POST or a GET operation.
        """
        url = REMOTE_SERVICE_URL.format(
            server=self._account.server_url,
            vin=self._vehicle.vin,
            service_type=service_id.value.lower().replace('_', '-')
        )
        params = {"action": action}
        response = self._account.send_request(url, post=post, params=params, brand=self._vehicle.brand)
        try:
            return response.json().get('eventId')
        except JSONDecodeError:
            return None

    def _block_until_done(self, service: _Services = None, event_id: str = None) -> RemoteServiceStatus:
        """Keep polling the server until we get a final answer.

        :raises IOError: if there is no final answer before _POLLING_TIMEOUT
        """
        if not service and not event_id:
            raise ValueError("One of 'service' or 'event_id' is required.")
        fail_after = datetime.datetime.now() + datetime.timedelta(seconds=_POLLING_TIMEOUT)
        while True:
            status = self._get_remote_service_status(service, event_id)
            _LOGGER.debug('current state if remote service is: %s', status.state.value)
            if status.state not in [ExecutionState.UNKNOWN, ExecutionState.PENDING, ExecutionState.DELIVERED]:
                return status
            if datetime.datetime.now() > fail_after:
                raise TimeoutError(
                    'Did not receive remote service result in {} seconds. Current state: {}'.format(
                        _POLLING_TIMEOUT,
                        status.state.value
                    ))
            time.sleep(_POLLING_CYCLE)

    def _get_remote_service_status(self, service: _Services = None, event_id: str = None) -> RemoteServiceStatus:
        """The the execution status of the last remote service that was triggered.

        As the status changes over time, you probably need to poll this.
        Recommended polling time is AT LEAST one second as the reaction is sometimes quite slow.
        """
        if not service and not event_id:
            raise ValueError("One of 'service' or 'event_id' is required.")
        _LOGGER.debug('getting remote service status')
        url = REMOTE_SERVICE_STATUS_URL.format(
            server=self._account.server_url,
            vin=self._vehicle.vin,
            event_id=event_id)
        response = self._account.send_request(url, post=True, brand=self._vehicle.brand)
        try:
            json_result = response.json()
            return RemoteServiceStatus(json_result)
        except ValueError:
            _LOGGER.error('Error decoding json response from the server.')
            _LOGGER.debug(response.headers)
            _LOGGER.debug(response.text)
            raise

    def _trigger_state_update(self) -> None:
        time.sleep(_UPDATE_AFTER_REMOTE_SERVICE_DELAY)
        self._account.update_vehicle_states()

    def trigger_send_poi(self, data: dict) -> RemoteServiceStatus:
        """Send a PointOfInterest to the vehicle.

        :param data: A dictonary containing at least 'lat' and 'lon' and optionally
            'name', 'additionalInfo', 'street', 'city', 'postalCode', 'country',
            'website' or 'phoneNumbers'
        :type data: dict

        A state update is NOT triggered after this, as the vehicle state is unchanged.
        """

        _LOGGER.debug('Sending PointOfInterest to car')
        if "lat" not in data or "lon" not in data:
            raise TypeError("__init__() missing 2 required positional arguments: 'lat' and 'lon'")

        data_json = json.dumps({
            "location": {
                "coordinates": {
                    "latitude": data["lat"],
                    "longitude": data["lon"]
                },
                "name": data.get('name'),
                "locationAddress": {
                    "street": data.get('street'),
                    "postalCode": data.get('postal_code'),
                    "city": data.get('city'),
                    "country": data.get('country'),
                },
                "type": "SHARED_DESTINATION_FROM_EXTERNAL_APP"
            },
            "vin": self._vehicle.vin
        })
        self._account.send_request(
            VEHICLE_POI_URL.format(server=self._account.server_url),
            post=True,
            headers={"Content-Type": "application/json"},
            data=data_json,
            brand=self._vehicle.brand
        )
        # _send_message has no separate ExecutionStates
        return RemoteServiceStatus({'eventStatus': 'EXECUTED'})

    def trigger_remote_vehicle_finder(self) -> RemoteServiceStatus:
        """Trigger the vehicle finder.

        A state update is triggered after this, as the location state of the vehicle changes.
        """
        _LOGGER.debug('Triggering remote vehicle finder')
        # needs to be called via POST, GET is not working
        event_id = self._trigger_remote_service(_Services.REMOTE_VEHICLE_FINDER)
        status = self._block_until_done(_Services.REMOTE_VEHICLE_FINDER, event_id)
        # Sleep another cycle to make sure the results are available
        time.sleep(_POLLING_CYCLE)
        result = self._get_event_position(event_id)
        self._vehicle.status.set_remote_service_position(result)
        return status
