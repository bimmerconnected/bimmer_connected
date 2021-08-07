"""Library to read data from the BMW Connected Drive portal.

The library bimmer_connected provides a Python interface to interact
with the BMW Connected Drive web service. It allows you to read
the current state of the vehicle and also trigger remote services.

Disclaimer:
This library is not affiliated with or endorsed by BMW Group.
"""

import datetime
import logging
import pathlib
import urllib
import json
from threading import Lock
from typing import Callable, List
import requests
from requests.exceptions import HTTPError

from bimmer_connected.country_selector import (
    Regions,
    get_server_url,
    get_gcdm_oauth_endpoint,
    get_gcdm_oauth_authorization
)
from bimmer_connected.vehicle import ConnectedDriveVehicle
from bimmer_connected.const import AUTH_URL, TOKEN_URL, VEHICLES_URL, ERROR_CODE_MAPPING

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

    # pylint: disable=too-many-arguments,too-many-locals
    def __init__(self, username: str, password: str, region: Regions, log_responses: pathlib.Path = None,
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
        self._lock = Lock()
        self._update_listeners = []

        self._get_vehicles()

    def _get_oauth_token(self) -> None:
        """Get a new auth token from the server."""
        with self._lock:
            if self._token_expiration is not None and datetime.datetime.now() < self._token_expiration:
                _LOGGER.debug('Old token is still valid. Not getting a new one.')
                return

            try:
                # We need a session for cross-request cookies
                oauth_session = requests.Session()

                _LOGGER.debug("Authenticating against GCDM.")
                authenticate_url = AUTH_URL.format(
                    gcdm_oauth_endpoint=get_gcdm_oauth_endpoint(self._region)
                )
                authenticate_headers = {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json, text/plain, */*",
                    "User-Agent": (
                        "Mozilla/5.0 (iPhone; CPU iPhone OS 12_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, "
                        "like Gecko) Version/12.1.2 Mobile/15E148 Safari/604.1"
                    ),
                }

                # we really need all of these parameters
                oauth_base_values = {
                    "client_id": "31c357a0-7a1d-4590-aa99-33b97244d048",
                    "response_type": "code",
                    "redirect_uri": "com.bmw.connected://oauth",
                    "state": "cEG9eLAIi6Nv-aaCAniziE_B6FPoobva3qr5gukilYw",
                    "nonce": "login_nonce",
                    "scope": (
                        "openid profile email offline_access smacc vehicle_data perseus dlm svds cesim vsapi "
                        "remote_services fupo authenticate_user"
                    ),
                }

                authenticate_data = urllib.parse.urlencode(
                    dict(
                        oauth_base_values,
                        **{
                            "grant_type": "authorization_code",
                            "username": self._username,
                            "password": self._password,
                        }
                    )
                )
                response = oauth_session.post(
                    authenticate_url, headers=authenticate_headers, data=authenticate_data
                )
                response.raise_for_status()
                authorization = dict(urllib.parse.parse_qsl(response.json()["redirect_to"]))["authorization"]
                _LOGGER.debug("got authorization challenge %s", authorization)

                code_data = urllib.parse.urlencode(
                    dict(oauth_base_values, **{"authorization": authorization})
                )
                response = oauth_session.post(
                    authenticate_url, headers=authenticate_headers, data=code_data, allow_redirects=False
                )
                response.raise_for_status()
                code = dict(urllib.parse.parse_qsl(response.next.path_url.split('?')[1]))["code"]
                _LOGGER.debug("got login code %s", code)

                _LOGGER.debug("getting new oauth token")
                token_url = TOKEN_URL.format(
                    gcdm_oauth_endpoint=get_gcdm_oauth_endpoint(self._region)
                )
                token_headers = {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "*/*",
                    "User-Agent": "My%20BMW/8932 CFNetwork/978.0.7 Darwin/18.7.0",
                }
                token_headers.update(get_gcdm_oauth_authorization(self._region))
                token_values = {
                    "code": code,
                    "code_verifier": "7PsmfPS5MpaNt0jEcPpi-B7M7u0gs1Nzw6ex0Y9pa-0",
                    "redirect_uri": "com.bmw.connected://oauth",
                    "grant_type": "authorization_code",
                }

                token_data = urllib.parse.urlencode(token_values)
                response = oauth_session.post(
                    token_url,
                    headers=token_headers,
                    data=token_data
                )
                response.raise_for_status()
                response_json = response.json()

                self._oauth_token = response_json["access_token"]
                expiration_time = int(response_json["expires_in"])
                self._token_expiration = datetime.datetime.now() + datetime.timedelta(
                    seconds=expiration_time
                )
                _LOGGER.debug(
                    "got new token %s with expiration date %s",
                    self._oauth_token,
                    self._token_expiration,
                )
            except HTTPError as ex:
                try:
                    err = response.json()
                    _LOGGER.error("Authentication failed (%s): %s", err["error"], err["error_description"])
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.error("Authentication failed: %s", response.text)
                raise ex
            except Exception as ex:  # pylint: disable=broad-except
                _LOGGER.exception(ex)
                raise ex

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

        while output_path is None or output_path.exists():
            output_path = self._log_responses / '{}_{}.txt'.format(logfilename, count)
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
            'name': 'some_name',
            'city': 'some_city',
            'street': 'some_street',
            'streetNumber': '999',
            'postalCode': 'some_postal_code',
            'phone': 'some_phone',
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
