"""Trigger remote services on a vehicle."""

from enum import Enum
import datetime
import logging
import requests
import json

REMOTE_SERVICE_URL = '{server}/api/vehicle/remoteservices/v1/{vin}/{service}'
MYINFO_URL = '{server}/api/vehicle/myinfo/v1'


TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'

_LOGGER = logging.getLogger(__name__)


class ExecutionState(Enum):
    """Enumeration of possible states of the execution of a remote service."""
    PENDING = 'PENDING'
    DELIVERED = 'DELIVERED_TO_VEHICLE'
    EXECUTED = 'EXECUTED'


class Services(Enum):
    """Enumeration of possible services to be executed."""
    REMOTE_LIGHT_FLASH = 'RLF'
    REMOTE_DOOR_LOCK = 'RDL'
    REMOTE_DOOR_UNLOCK = 'RDU'
    REMOTE_SERVICE_STATUS = 'state/execution'


class RemoteServiceStatus(object):  # pylint: disable=too-few-public-methods
    """Wraps the status of the execution of a remote service."""

    def __init__(self, response: dict):
        """Construct a new object from a dict."""
        self._response = response
        # the result from the service call is different from the status request
        # we need to go one level down in the response if possible
        if 'remoteServiceEvent' in response:
            response = response['remoteServiceEvent']
        self.state = ExecutionState(response['remoteServiceStatus'])
        self.timestamp = self._parse_timestamp(response['lastUpdate'])

    @staticmethod
    def _parse_timestamp(timestamp: str) -> datetime.datetime:
        """Parse the timestamp format from the response."""
        offset = int(timestamp[-3:])
        time_zone = datetime.timezone(datetime.timedelta(hours=offset))
        result = datetime.datetime.strptime(timestamp[:-3], TIME_FORMAT)
        result.replace(tzinfo=time_zone)
        return result


class RemoteServices(object):
    """Trigger remote services on a vehicle."""

    def __init__(self, account, vehicle):
        """Constructor."""
        self._account = account
        self._vehicle = vehicle

    def trigger_remote_light_flash(self):
        """Trigger the vehicle to flash its headlights."""
        _LOGGER.debug('Triggering remote light flash')
        # needs to be called via POST, GET is not working
        response = self._trigger_remote_service(Services.REMOTE_LIGHT_FLASH, post=True)
        return RemoteServiceStatus(response.json())

    def trigger_remote_door_lock(self):
        """Trigger the vehicle to lock its doors."""
        _LOGGER.debug('Triggering remote door lock')
        # needs to be called via POST, GET is not working
        response = self._trigger_remote_service(Services.REMOTE_DOOR_LOCK, post=True)
        return RemoteServiceStatus(response.json())

    def trigger_remote_door_unlock(self):
        """Trigger the vehicle to unlock its doors."""
        _LOGGER.debug('Triggering remote door lock')
        # needs to be called via POST, GET is not working
        response = self._trigger_remote_service(Services.REMOTE_DOOR_UNLOCK, post=True)
        return RemoteServiceStatus(response.json())

    def _trigger_remote_service(self, service_id: Services, post=False) -> requests.Response:
        """Trigger a generic remote service.

        You can choose if you want a POST or a GET operation.
        """
        url = REMOTE_SERVICE_URL.format(vin=self._vehicle.vin, service=service_id.value,
                                        server=self._account.server_url)

        return self._account.send_request(url, post=post)

    def get_remote_service_status(self):
        """The the execution status of the last remote service that was triggered.

        As the status changes over time, you probably need to poll this.
        Recommended polling time is AT LEAST one second as the reaction is sometimes quite slow.
        """
        response = self._trigger_remote_service(Services.REMOTE_SERVICE_STATUS)
        try:
            json_result = response.json()
            return RemoteServiceStatus(json_result)
        except ValueError:
            _LOGGER.error('Error decoding json response from the server.')
            _LOGGER.debug(response.headers)
            _LOGGER.debug(response.text)
            raise

    def send_notification(self, subject: str, message: str) -> None:
        """Send a text notification to the vehicle."""
        payload = {
            'vins': [self._vehicle.vin],
            'message': message,
            'subject': subject}
        data = json.dumps(payload)
        _LOGGER.debug('Sending message: "%s"', data)
        self._account.send_request(MYINFO_URL.format(server=self._account.server_url), data=data, post=True)
