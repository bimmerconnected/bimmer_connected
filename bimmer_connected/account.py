"""Library to read data from the BMW Connected Drive portal.

The library bimmer_connected provides a Python interface to interact
with the BMW Connected Drive web service. It allows you to read
the current state of the vehicle and also trigger remote services.

Disclaimer:
This library is not affiliated with or endorsed by BMW Group.
"""

import datetime
import logging
import urllib
import os
import json
from threading import Lock
from typing import Callable, List
import requests

from bimmer_connected.country_selector import Regions, get_server_url
from bimmer_connected.vehicle import ConnectedDriveVehicle
from bimmer_connected.const import AUTH_URL, VEHICLES_URL

_LOGGER = logging.getLogger(__name__)


class ConnectedDriveAccount:  # pylint: disable=too-many-instance-attributes
    """Create a new connection to the BMW Connected Drive web service.

    :param username: Connected drive user name
    :param password: Connected drive password
    :param country: Country for which the account was created. For a list of valid countries,
                check https://www.bmw-connecteddrive.com .
                Use the name of the countries exactly as on the website.
    :param log_responses: If log_responses is set, all responses from the server will
                be loged into this directory. This can be used for later analysis of the different
                responses for different vehicles.
    """

    # pylint: disable=too-many-arguments
    def __init__(self, username: str, password: str, region: Regions, log_responses: str = None) -> None:
        self._region = region
        self._server_url = None
        self._username = username
        self._password = password
        self._oauth_token = None
        self._refresh_token = None
        self._token_expiration = None
        self._log_responses = log_responses
        #: list of vehicles associated with this account.
        self._vehicles = []
        self._lock = Lock()
        self._update_listeners = []

        self._get_vehicles()

    def _get_oauth_token(self) -> None:
        """Get a new auth token from the server."""
        with self._lock:
            if self._token_expiration is not None and datetime.datetime.now() < self._token_expiration:
                _LOGGER.debug('Old token is still valid. Not getting a new one.')
                return

            _LOGGER.debug('getting new oauth token')
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Content-Length": "124",
                "Connection": "Keep-Alive",
                "Host": self.server_url,
                "Accept-Encoding": "gzip",
                "Authorization": "Basic blF2NkNxdHhKdVhXUDc0eGYzQ0p3VUVQOjF6REh4NnVuNGNEanli"
                                 "TEVOTjNreWZ1bVgya0VZaWdXUGNRcGR2RFJwSUJrN3JPSg==",
                "Credentials": "nQv6CqtxJuXWP74xf3CJwUEP:1zDHx6un4cDjybLENN3kyfumX2kEYigWPcQpdvDRpIBk7rOJ",
                "User-Agent": "okhttp/2.60",
            }

            # we really need all of these parameters
            values = {
                'grant_type': 'password',
                'scope': 'authenticate_user vehicle_data remote_services',
                'username': self._username,
                'password': self._password,
            }

            data = urllib.parse.urlencode(values)
            url = AUTH_URL.format(server=self.server_url)
            try:
                response = self.send_request(url, data=data, headers=headers, allow_redirects=False,
                                             expected_response=200, post=True)
            except OSError as exception:
                msg = 'Authentication failed. Maybe your password is invalid?'
                _LOGGER.error(msg)
                _LOGGER.exception(exception)
                raise OSError(msg) from exception

            response_json = response.json()
            self._oauth_token = response_json['access_token']
            # not sure how to use the refresh_token, but might be useful in the future...
            self._refresh_token = response_json['refresh_token']
            expiration_time = response_json['expires_in']
            self._token_expiration = datetime.datetime.now() + datetime.timedelta(seconds=expiration_time)
            _LOGGER.debug('got new token %s with expiration date %s', self._oauth_token, self._token_expiration)

    @property
    def request_header(self):
        """Generate a header for HTTP requests to the server."""
        self._get_oauth_token()
        headers = {
            "accept": "application/json",
            "Authorization": "Bearer {}".format(self._oauth_token),
            "referer": "https://www.bmw-connecteddrive.de/app/index.html",
        }
        return headers

    def send_request(self, url: str, data=None, headers=None, expected_response=200, post=False, allow_redirects=True,
                     logfilename: str = None, params: dict = None):
        """Send an http request to the server.

        If the http headers are not set, default headers are generated.
        You can choose if you want a GET or POST request.
        """
        if headers is None:
            headers = self.request_header

        if post:
            response = requests.post(url, headers=headers, data=data, allow_redirects=allow_redirects, params=params)
        else:
            response = requests.get(url, headers=headers, data=data, allow_redirects=allow_redirects, params=params)

        if response.status_code != expected_response:
            msg = 'Unknown status code {}, expected {}'.format(response.status_code, expected_response)
            _LOGGER.error(msg)
            _LOGGER.error(response.text)
            raise IOError(msg)
        self._log_response_to_file(response, logfilename)
        return response

    def _log_response_to_file(self, response: requests.Response, logfilename: str = None) -> None:
        """If a log path is set, log all resonses to a file."""
        if self._log_responses is None or logfilename is None:
            return

        anonymized_data = json.dumps(self._anonymize_data(response.json()), indent=2, sort_keys=True)

        output_path = None
        count = 0

        while output_path is None or os.path.exists(output_path):
            output_path = os.path.join(self._log_responses, '{}_{}.txt'.format(logfilename, count))
            count += 1

        with open(output_path, 'w') as logfile:
            logfile.write(anonymized_data)

    @staticmethod
    def _anonymize_data(json_data: dict) -> dict:
        """Replace parts of the logfiles containing personal information."""

        replacements = {
            'lat': 12.3456,
            'lon': 34.5678,
            'heading': 123,
            'vin': 'some_vin',
            'licensePlate': 'some_license_plate',
        }

        if isinstance(json_data, list):
            json_data = [ConnectedDriveAccount._anonymize_data(v) for v in json_data]
        elif isinstance(json_data, dict):
            for key, value in json_data.items():
                if key in replacements:
                    json_data[key] = replacements[key]
                else:
                    json_data[key] = ConnectedDriveAccount._anonymize_data(value)

        return json_data

    @property
    def server_url(self) -> str:
        """Get the url of the server for this country."""
        if self._server_url is None:
            self._server_url = get_server_url(self._region)
        return self._server_url

    def _get_vehicles(self):
        """Retrieve list of vehicle for the account."""
        _LOGGER.debug('Getting vehicle list')
        self._get_oauth_token()
        response = self.send_request(VEHICLES_URL.format(server=self.server_url), headers=self.request_header,
                                     logfilename='vehicles')

        for vehicle_dict in response.json()['vehicles']:
            self._vehicles.append(ConnectedDriveVehicle(self, vehicle_dict))

    def get_vehicle(self, vin: str) -> ConnectedDriveVehicle:
        """Get vehicle with given VIN.

        The search is NOT case sensitive.
        :param vin: VIN of the vehicle you want to get.
        :return: Returns None if no such vehicle is found.
        """
        for car in self.vehicles:
            if car.vin.upper() == vin.upper():
                return car
        return None

    def update_vehicle_states(self) -> None:
        """Update the state of all vehicles.

        Notify all listeners of the vehicle state update.
        """
        for car in self.vehicles:
            car.update_state()
        for listener in self._update_listeners:
            listener()

    def add_update_listener(self, listener: Callable) -> None:
        """Add a listener for state updates."""
        self._update_listeners.append(listener)

    @property
    def vehicles(self) -> List[ConnectedDriveVehicle]:
        """Get list of vehicle of this account"""
        return self._vehicles

    def __str__(self):
        """Use the user name as id for the account class."""
        return '{}: {}'.format(self.__class__, self._username)

    def set_observer_position(self, latitude: float, longitude: float) -> None:
        """Set the position of the observer for all vehicles.

        see VehicleViewDirection.set_observer_position() for more details.
        """
        if bool(latitude) != bool(longitude):
            raise ValueError('Either latitude and longitude are both not None or both are None.')
        if latitude and longitude:
            for vehicle in self._vehicles:
                vehicle.set_observer_position(latitude, longitude)
