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
from threading import RLock
from typing import Callable, List
import requests

from bimmer_connected.country_selector import Regions, LoginType, get_server_url, get_auth_url, get_login_type
from bimmer_connected.vehicle import ConnectedDriveVehicle
from bimmer_connected.const import BASE_URL, VEHICLES_URL, ERROR_CODE_MAPPING

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
    :param retries_on_500_error: If retries_on_500_error is set, a communication with the
                Connected Drive server will automatically be retried the number of times
                specified in the event the error code received was 500. This sometimes
                occurs (presumably) due to bugs in the server implementation.
    """

    # pylint: disable=too-many-arguments
    def __init__(self, username: str, password: str, region: Regions, log_responses: str = None,
                 retries_on_500_error: int = 5) -> None:
        self._region = region
        self._server_url = None
        self._username = username
        self._password = password
        self._oauth_token = None
        self._refresh_token = None
        self._token_expiration = None
        self._log_responses = log_responses
        self._retries_on_500_error = retries_on_500_error
        #: list of vehicles associated with this account.
        self._vehicles = []
        self._lock = RLock()
        self._update_listeners = []

        self._get_vehicles()

    def _get_oauth_token(self) -> None:
        """Get a new auth token from the server, based on user GCDM tokens"""

        with self._lock:
            if self._token_expiration is not None and datetime.datetime.now() < self._token_expiration:
                _LOGGER.debug('Old token is still valid. Not getting a new one.')
                return

            _LOGGER.debug('getting new oauth token')

            _base_url = BASE_URL.format(server=get_server_url(self._region))
            # Get GCDM tokens with username/password
            gcdm_tokens = self._get_gcdm_token()

            if get_login_type(self._region) == LoginType.LEGACY:
                oauth_tokens = gcdm_tokens
            else:
                # We need a session for cross-request cookies
                oauth_session = requests.Session()

                # Generate a state_token for OAuth (but don't sign in yet)
                oauth_headers = {"ocp-apim-subscription-key": "4be77952d6fe4f25a5e398fd84c77965"}
                oauth_state_request = oauth_session.get(
                    url=_base_url + "/api/Account/ExternalLogin",
                    headers=oauth_headers,
                    params={
                        "provider": "GCDM",
                        "response_type": "token",
                        "redirect_uri": _base_url + "/",
                        "client_id": "self",
                    },
                )
                state_token = urllib.parse.parse_qs(oauth_state_request.url).get("state")[0]

                # With state_token, GCDM access_token and GCDM refresh_token, retrieve a authenticated session cookie
                oauth_session.get(
                    url=_base_url + "/oauth_callback.html",
                    headers=oauth_headers,
                    params={
                        "scope": "authenticate_user",
                        "refresh": gcdm_tokens["refresh_token"],
                        "state": state_token,
                        "token": gcdm_tokens["access_token"],
                    },
                    allow_redirects=False,
                )

                # With the session cookie, call External Login again to get OAuth access_token, refresh_token and expiry
                oauth_token_request = oauth_session.get(
                    url=_base_url + "/api/Account/ExternalLogin",
                    headers=oauth_headers,
                    params={
                        "provider": "GCDM",
                        "response_type": "token",
                        "redirect_uri": _base_url + "/",
                        "client_id": "self",
                    },
                )
                oauth_tokens = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(oauth_token_request.url).fragment))

            self._oauth_token = oauth_tokens['access_token']
            # not sure how to use the refresh_token, but might be useful in the future...
            self._refresh_token = oauth_tokens['refresh_token']
            expiration_time = int(oauth_tokens['expires_in'])
            self._token_expiration = datetime.datetime.now() + datetime.timedelta(seconds=expiration_time)
            _LOGGER.debug('got new token %s with expiration date %s', self._oauth_token, self._token_expiration)

    def _get_gcdm_token(self) -> dict:
        """Get a new GCDM (Global Customer Data Management) token from the server."""
        with self._lock:

            _LOGGER.debug('getting new GCDM token')
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": "Basic ZDc2NmI1MzctYTY1NC00Y2JkLWEzZGMtMGNhNTY3MmQ3ZjhkOjE1"
                                 "ZjY5N2Y2LWE1ZDUtNGNhZC05OWQ5LTNhMTViYzdmMzk3Mw==",
                "Credentials": "ZDc2NmI1MzctYTY1NC00Y2JkLWEzZGMtMGNhNTY3MmQ3Zjhk:"
                               "M2YxYzBjZGEtMDgyOC00Y2RjLWFiMmEtMDY2YzJhMjY0ODAz",
            }

            # we really need all of these parameters
            values = {
                'grant_type': 'password',
                'scope': 'authenticate_user vehicle_data remote_services',
                'username': self._username,
                'password': self._password,
            }

            data = urllib.parse.urlencode(values)
            try:
                response = self.send_request(
                    BASE_URL.format(server=get_auth_url(self._region)),
                    data=data,
                    headers=headers,
                    allow_redirects=False,
                    expected_response=200,
                    post=True)
            except OSError as exception:
                msg = 'Authentication failed. Maybe your password is invalid?'
                _LOGGER.error(msg)
                _LOGGER.exception(exception)
                raise OSError(msg) from exception
            response_json = response.json()
            _LOGGER.debug('got new GCDM token %s', response_json['access_token'])
            return response.json()

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

        for i in range(self._retries_on_500_error + 1):
            if post:
                response = requests.post(url, headers=headers, data=data, allow_redirects=allow_redirects,
                                         params=params)
            else:
                response = requests.get(url, headers=headers, data=data, allow_redirects=allow_redirects,
                                        params=params)

            if response.status_code != expected_response:
                if response.status_code == 500:
                    _LOGGER.debug("Error 500 on attempt %d", i+1)
                    continue

                error_description = ERROR_CODE_MAPPING.get(response.status_code, "UNKNOWN_ERROR")
                msg = ("The BMW Connected Drive portal returned an error: {} (received status code {} and expected {})."
                       .format(error_description, response.status_code, expected_response))
                _LOGGER.debug(msg)
                _LOGGER.debug(response.text)
                raise IOError(msg)
            break

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
