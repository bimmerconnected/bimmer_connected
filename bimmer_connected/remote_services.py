"""Trigger remote services on a vehicle."""

import datetime
import json
import logging
import time
from typing import List
from enum import Enum
from urllib.parse import urlencode

import requests

from bimmer_connected.const import (REMOTE_SERVICE_STATUS_URL,
                                    REMOTE_SERVICE_URL,
                                    VEHICLE_POI_URL)

TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'

_LOGGER = logging.getLogger(__name__)

#: time in seconds between polling updates on the status of a remote service
_POLLING_CYCLE = 1

#: maximum number of seconds to wait for the server to return a positive answer
_POLLING_TIMEOUT = 120

#: time in seconds to wait before updating the vehicle state from the server
_UPDATE_AFTER_REMOTE_SERVICE_DELAY = 10


class ExecutionState(Enum):
    """Enumeration of possible states of the execution of a remote service."""
    INITIATED = 'INITIATED'
    PENDING = 'PENDING'
    DELIVERED = 'DELIVERED'
    EXECUTED = 'EXECUTED'
    UNKNOWN = 'UNKNOWN'


class _Services(Enum):
    """Enumeration of possible services to be executed."""
    REMOTE_LIGHT_FLASH = 'LIGHT_FLASH'
    REMOTE_VEHICLE_FINDER = 'VEHICLE_FINDER'
    REMOTE_DOOR_LOCK = 'DOOR_LOCK'
    REMOTE_DOOR_UNLOCK = 'DOOR_UNLOCK'
    REMOTE_HORN = 'HORN_BLOW'
    REMOTE_AIR_CONDITIONING = 'CLIMATE_NOW'


# pylint: disable=too-many-instance-attributes, too-few-public-methods
class PointOfInterest:
    """Point of interest to be sent to the vehicle.

    The latitude/longitude of a POI are mandatory, all other attributes are optional. CamelCase attribute names are
    used here so that we do not have to convert the names between the attributes and the keys as expected on the server.
    """

    # pylint: disable=too-many-arguments
    def __init__(self, lat: float, lon: float, name: str = None,
                 additional_info: str = None, street: str = None, city: str = None,
                 postal_code: str = None, country: str = None, website: str = None,
                 phone_numbers: List[str] = None):
        """Create a PointOfInterest with attributes in camelCase as required by the API.

        :arg lat: latitude of the POI
        :arg lon: longitude of the POI
        :arg name: name of the POI (Optional)
        :arg additional_info: additional text shown below the address (Optional)
        :arg street: street with house number of the POI (Optional)
        :arg city: city of the POI (Optional)
        :arg postal_code: zip code of the POI (Optional)
        :arg country: country of the POI (Optional)
        :arg website: website of the POI (Optional)
        :arg phone_numbers: List of phone numbers of the POI (Optional)
        """
        # pylint: disable=invalid-name
        self.lat = lat  # type: float
        self.lon = lon  # type: float
        self.name = name  # type: str
        self.additionalInfo = additional_info if additional_info is not None \
            else 'Sent with ♥ by bimmer_connected'  # type: str
        self.street = street  # type: str
        self.city = city  # type: str
        self.postalCode = postal_code  # type: str
        self.country = country  # type: str
        self.website = website  # type: str
        self.phoneNumbers = phone_numbers  # type: list[str]


class Message:
    """Text message or PointOfInterst to be sent to the vehicle."""

    @classmethod
    def from_poi(cls, poi: PointOfInterest):
        """Create a message from a PointOfInterest"""
        return cls(poi.__dict__)

    @classmethod
    def from_text(cls, text: str, subject: str = None):
        """Create a text message"""
        return cls({"name": subject, "additionalInfo": text[:255]})

    def __init__(self, data: dict):
        self.data = data

    @property
    def as_server_request(self) -> str:
        """Convert to a dictionary so that it can be sent to the server."""
        result = {
            'poi': {k: v for k, v in self.data.items() if v is not None}
        }
        return urlencode({'data': json.dumps(result)})


class RemoteServiceStatus:  # pylint: disable=too-few-public-methods
    """Wraps the status of the execution of a remote service."""

    def __init__(self, response: dict):
        """Construct a new object from a dict."""
        status = response.get('executionStatus', {})
        if len(status) == 0:
            _LOGGER.warning("executionStatus not in response: %s", response)

        self.state = ExecutionState(status.get('status', 'UNKNOWN'))
        self.event_id = status.get('eventId')

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
        _LOGGER.debug('Triggering remote door unlock')
        # needs to be called via POST, GET is not working
        self._trigger_remote_service(_Services.REMOTE_DOOR_UNLOCK, post=True)
        result = self._block_until_done(_Services.REMOTE_DOOR_UNLOCK)
        self._trigger_state_update()
        return result

    def trigger_remote_horn(self) -> RemoteServiceStatus:
        """Trigger the vehicle to sound its horn.

        A state update is NOT triggered after this, as the vehicle state is unchanged.
        """
        _LOGGER.debug('Triggering remote horn sound')
        # needs to be called via POST, GET is not working
        self._trigger_remote_service(_Services.REMOTE_HORN, post=True)
        return self._block_until_done(_Services.REMOTE_HORN)

    def trigger_remote_air_conditioning(self) -> RemoteServiceStatus:
        """Trigger the air conditioning to start.

        A state update is NOT triggered after this, as the vehicle state is unchanged.
        """
        _LOGGER.debug('Triggering remote air conditioning')
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
            if status.state not in [ExecutionState.UNKNOWN, ExecutionState.PENDING, ExecutionState.DELIVERED]:
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

    def trigger_send_message(self, data: dict) -> RemoteServiceStatus:
        """Send a message to the vehicle.

        :param data: A dictonary containing a 'text' and an optional 'subject'
        :type data: dict

        A state update is NOT triggered after this, as the vehicle state is unchanged.
        """
        _LOGGER.debug('Sending message to car')
        if "text" not in data:
            raise TypeError("from_text() missing 1 required positional argument: 'text'")
        self._send_message(Message.from_text(data['text'], data.get('subject')))
        # _send_message has no separate ExecutionStates
        return RemoteServiceStatus({'executionStatus': {'status': 'EXECUTED', 'eventId': -1}})

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
        poi = PointOfInterest(**data)
        self._send_message(Message.from_poi(poi))
        # _send_message has no separate ExecutionStates
        return RemoteServiceStatus({'executionStatus': {'status': 'EXECUTED', 'eventId': -1}})

    def _send_message(self, msg: Message) -> None:
        """Send a message/point of interest to the vehicle."""
        url = VEHICLE_POI_URL.format(
            vin=self._vehicle.vin,
            server=self._account.server_url
        )
        header = self._account.request_header
        # the accept field of the header needs to be updated not the usual JSON
        header['Content-Type'] = 'application/x-www-form-urlencoded'
        return self._account.send_request(url,
                                          headers=header,
                                          data=msg.as_server_request,
                                          post=True,
                                          expected_response=204)

    def trigger_remote_vehicle_finder(self) -> RemoteServiceStatus:
        """Trigger the vehicle finder.

        A state update is triggered after this, as the location state of the vehicle changes.
        """
        _LOGGER.debug('Triggering remote vehicle finder')
        # needs to be called via POST, GET is not working
        self._trigger_remote_service(_Services.REMOTE_VEHICLE_FINDER, post=True)
        result = self._block_until_done(_Services.REMOTE_VEHICLE_FINDER)
        self._trigger_state_update()
        return result
