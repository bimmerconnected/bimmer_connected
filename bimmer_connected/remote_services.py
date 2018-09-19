"""Trigger remote services on a vehicle."""

from enum import Enum
import datetime
import logging
import time
import requests
from bimmer_connected.const import REMOTE_SERVICE_URL, REMOTE_SERVICE_STATUS_URL


TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'

_LOGGER = logging.getLogger(__name__)

#: time in seconds between polling updates on the status of a remote service
_POLLING_CYCLE = 1

#: maximum number of seconds to wait for the server to return a positive answer
_POLLING_TIMEOUT = 60

#: time in seconds to wait before updating the vehicle state from the server
_UPDATE_AFTER_REMOTE_SERVICE_DELAY = 10


class ExecutionState(Enum):
    """Enumeration of possible states of the execution of a remote service."""
    INITIATED = 'INITIATED'
    PENDING = 'PENDING'
    DELIVERED = 'DELIVERED'
    EXECUTED = 'EXECUTED'


class _Services(Enum):
    """Enumeration of possible services to be executed."""
    REMOTE_LIGHT_FLASH = 'LIGHT_FLASH'
    REMOTE_DOOR_LOCK = 'DOOR_LOCK'
    REMOTE_DOOR_UNLOCK = 'DOOR_UNLOCK'
    REMOTE_HORN = 'HORN_BLOW'
    REMOTE_AIR_CONDITIONING = 'CLIMATE_NOW'


class RemoteServiceStatus:  # pylint: disable=too-few-public-methods
    """Wraps the status of the execution of a remote service."""

    def __init__(self, response: dict):
        """Construct a new object from a dict."""
        status = response['executionStatus']
        self.state = ExecutionState(status['status'])
        self.event_id = status['eventId']

    @staticmethod
    def _parse_timestamp(timestamp: str) -> datetime.datetime:
        """Parse the timestamp format from the response."""
        offset = int(timestamp[-3:])
        time_zone = datetime.timezone(datetime.timedelta(hours=offset))
        result = datetime.datetime.strptime(timestamp[:-3], TIME_FORMAT)
        result.replace(tzinfo=time_zone)
        return result


class RemoteServices:
    """Trigger remote services on a vehicle."""

    def __init__(self, account, vehicle):
        """Constructor."""
        self._account = account
        self._vehicle = vehicle

    def trigger_remote_light_flash(self) -> RemoteServiceStatus:
        """Trigger the vehicle to flash its headlights.

        A state update is NOT triggered after this, as the vehicle state is unchanged.
        """
        _LOGGER.debug('Triggering remote light flash')
        # needs to be called via POST, GET is not working
        self._trigger_remote_service(_Services.REMOTE_LIGHT_FLASH, post=True)
        return self._block_until_done(_Services.REMOTE_LIGHT_FLASH)

    def trigger_remote_door_lock(self) -> RemoteServiceStatus:
        """Trigger the vehicle to lock its doors.

        A state update is triggered after this, as the lock state of the vehicle changes.
        """
        _LOGGER.debug('Triggering remote door lock')
        # needs to be called via POST, GET is not working
        self._trigger_remote_service(_Services.REMOTE_DOOR_LOCK, post=True)
        result = self._block_until_done(_Services.REMOTE_DOOR_LOCK)
        self._trigger_state_update()
        return result

    def trigger_remote_door_unlock(self) -> RemoteServiceStatus:
        """Trigger the vehicle to unlock its doors.

        A state update is triggered after this, as the lock state of the vehicle changes.
        """
        _LOGGER.debug('Triggering remote door lock')
        # needs to be called via POST, GET is not working
        self._trigger_remote_service(_Services.REMOTE_DOOR_UNLOCK, post=True)
        result = self._block_until_done(_Services.REMOTE_DOOR_UNLOCK)
        self._trigger_state_update()
        return result

    def trigger_remote_horn(self) -> RemoteServiceStatus:
        """Trigger the vehicle to sound its horn.

        A state update is NOT triggered after this, as the vehicle state is unchanged.
        """
        _LOGGER.debug('Triggering remote light flash')
        # needs to be called via POST, GET is not working
        self._trigger_remote_service(_Services.REMOTE_HORN, post=True)
        return self._block_until_done(_Services.REMOTE_HORN)

    def trigger_remote_air_conditioning(self) -> RemoteServiceStatus:
        """Trigger the vehicle to sound its horn.

        A state update is NOT triggered after this, as the vehicle state is unchanged.
        """
        _LOGGER.debug('Triggering remote light flash')
        # needs to be called via POST, GET is not working
        self._trigger_remote_service(_Services.REMOTE_AIR_CONDITIONING, post=True)
        result = self._block_until_done(_Services.REMOTE_AIR_CONDITIONING)
        self._trigger_state_update()
        return result

    def _trigger_remote_service(self, service_id: _Services, post=False) -> requests.Response:
        """Trigger a generic remote service.

        You can choose if you want a POST or a GET operation.
        """
        data = {'serviceType': service_id.value}
        url = REMOTE_SERVICE_URL.format(vin=self._vehicle.vin, server=self._account.server_url)

        return self._account.send_request(url, post=post, data=data)

    def _block_until_done(self, service: _Services) -> RemoteServiceStatus:
        """Keep polling the server until we get a final answer.

        :raises IOError: if there is no final answer before _POLLING_TIMEOUT
        """
        fail_after = datetime.datetime.now() + datetime.timedelta(seconds=_POLLING_TIMEOUT)
        while True:
            status = self._get_remote_service_status(service)
            _LOGGER.debug('current state if remote service is: %s', status.state.value)
            if status.state not in [ExecutionState.PENDING, ExecutionState.DELIVERED]:
                return status
            if datetime.datetime.now() > fail_after:
                raise IOError(
                    'Timeout on getting final answer from server. Current state: {}'.format(status.state.value))
            time.sleep(_POLLING_CYCLE)

    def _get_remote_service_status(self, service: _Services) -> RemoteServiceStatus:
        """The the execution status of the last remote service that was triggered.

        As the status changes over time, you probably need to poll this.
        Recommended polling time is AT LEAST one second as the reaction is sometimes quite slow.
        """
        _LOGGER.debug('getting remote service status')
        url = REMOTE_SERVICE_STATUS_URL.format(
            server=self._account.server_url,
            vin=self._vehicle.vin,
            service_type=service.value)
        response = self._account.send_request(url)
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
