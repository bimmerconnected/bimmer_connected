"""Library to read data from the BMW Connected Drive portal.

The library bimmer_connected provides a Python interface to interact
with the BMW Connected Drive web service. It allows you to read
the current state of the vehicle and also trigger remote services.

Disclaimer:
This library is not affiliated with or endorsed by BMW Group.
"""

import base64
import datetime
import hashlib
import json
import logging
import os
import pathlib
import urllib
from threading import Lock
from typing import Any, Callable, Dict, List
import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError
from requests.models import Response

from bimmer_connected.country_selector import (
    Regions,
    get_server_url,
    get_ocp_apim_key,
)
from bimmer_connected.vehicle import ConnectedDriveVehicle, CarBrand
from bimmer_connected.const import AUTH_URL, OAUTH_CONFIG_URL, VEHICLES_URL, X_USER_AGENT

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
        self._server_url_legacy = None
        self._server_url = None
        self._username = username
        self._password = password
        self._oauth_token = None
        self._refresh_token = None
        self._token_expiration = None
        self._log_responses = log_responses
        self._retries_on_500_error = retries_on_500_error
        #: list of vehicles associated with this account.
        self._vehicles = []  # type: list[ConnectedDriveVehicle]
        self._lock = Lock()
        self._update_listeners = []  # type: list[Callable[[], Any]]

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
                # oauth_settings = get_gcdm_oauth_authorization(self._region)
                r_oauth_settings = oauth_session.get(
                    OAUTH_CONFIG_URL.format(server=self.server_url),
                    headers={
                        "ocp-apim-subscription-key": get_ocp_apim_key(self._region),
                        "x-user-agent": X_USER_AGENT.format("bmw"),
                    }
                )
                r_oauth_settings.raise_for_status()
                oauth_settings = r_oauth_settings.json()

                # My BMW login flow
                _LOGGER.debug("Authenticating against GCDM with MyBMW flow.")

                # Setting up PKCS data
                verifier_bytes = os.urandom(64)
                code_verifier = base64.urlsafe_b64encode(verifier_bytes).rstrip(b'=')

                challenge_bytes = hashlib.sha256(code_verifier).digest()
                code_challenge = base64.urlsafe_b64encode(challenge_bytes).rstrip(b'=')

                state_bytes = os.urandom(16)
                state = base64.urlsafe_b64encode(state_bytes).rstrip(b'=')

                authenticate_url = AUTH_URL.format(gcdm_base_url=oauth_settings["gcdmBaseUrl"])
                authenticate_headers = {
                    "Content-Type": "application/x-www-form-urlencoded",
                }

                # we really need all of these parameters
                oauth_base_values = {
                    "client_id": oauth_settings["clientId"],
                    "response_type": "code",
                    "redirect_uri": oauth_settings["returnUrl"],
                    "state": state,
                    "nonce": "login_nonce",
                    "scope": " ".join(oauth_settings["scopes"]),
                    "code_challenge": code_challenge,
                    "code_challenge_method": "S256",
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
                    authenticate_url,
                    headers=authenticate_headers,
                    data=authenticate_data,
                )
                response.raise_for_status()
                authorization = dict(urllib.parse.parse_qsl(response.json()["redirect_to"]))["authorization"]

                code_data = urllib.parse.urlencode(
                    dict(oauth_base_values, **{"authorization": authorization})
                )
                response = oauth_session.post(
                    authenticate_url, headers=authenticate_headers, data=code_data, allow_redirects=False
                )
                response.raise_for_status()
                code = dict(urllib.parse.parse_qsl(response.next.path_url.split('?')[1]))["code"]

                token_url = oauth_settings["tokenEndpoint"]

                # My BMW login flow
                token_headers = {
                    "Content-Type": "application/x-www-form-urlencoded",
                    # "Authorization": oauth_settings["token"]["Authorization"],
                }
                token_values = {
                    "code": code,
                    "code_verifier": code_verifier,
                    "redirect_uri": oauth_settings["returnUrl"],
                    "grant_type": "authorization_code",
                }

                token_data = urllib.parse.urlencode(token_values)
                response = oauth_session.post(
                    token_url,
                    headers=token_headers,
                    data=token_data,
                    auth=HTTPBasicAuth(oauth_settings["clientId"], oauth_settings["clientSecret"])
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

    def request_header(self, brand: CarBrand = None) -> Dict[str, str]:
        """Generate a header for HTTP requests to the server."""
        self._get_oauth_token()
        brand = brand or CarBrand.BMW
        headers = {
            "accept": "application/json",
            "x-user-agent": X_USER_AGENT.format(brand.value),
            "Authorization": "Bearer {}".format(self._oauth_token),
        }
        return headers

    def send_request(self, url: str, data=None, headers=None, post=False, allow_redirects=True,
                     logfilename: str = None, params: dict = None, brand: CarBrand = None) -> Response:
        """Send an http request to the server.

        If the http headers are not set, default headers are generated.
        You can choose if you want a GET or POST request.
        """
        _LOGGER.debug("Request to: %s", url)
        self._get_oauth_token()
        request_headers = self.request_header(brand)
        if headers:
            request_headers.update(headers)

        if post:
            response = requests.post(url, headers=request_headers, data=data, allow_redirects=allow_redirects,
                                     params=params)
        else:
            response = requests.get(url, headers=request_headers, data=data, allow_redirects=allow_redirects,
                                    params=params)

        try:
            response.raise_for_status()
        except HTTPError as ex:
            _LOGGER.exception(ex)
            raise ex

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

        with open(output_path, 'w', encoding='UTF-8') as logfile:
            logfile.write(anonymized_data)

    @staticmethod
    def _anonymize_data(json_data: dict) -> dict:
        """Replace parts of the logfiles containing personal information."""

        replacements = {
            'lat': 12.3456,
            'latitude': 12.3456,
            'lon': 34.5678,
            'longitude': 34.5678,
            'heading': 123,
            'vin': 'some_vin',
            'licensePlate': 'some_license_plate',
            'name': 'some_name',
            'city': 'some_city',
            'street': 'some_street',
            'streetNumber': '999',
            'postalCode': 'some_postal_code',
            'phone': 'some_phone',
            'formatted': 'some_formatted_address',
            'subtitle': 'some_road \u2022 duration \u2022 -- EUR',
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

    @property
    def region(self) -> str:
        """Get the region."""
        return self._region

    def _get_vehicles(self) -> None:
        """Retrieve list of vehicle for the account."""
        _LOGGER.debug('Getting vehicle list')
        self._get_oauth_token()

        for brand in CarBrand:
            response = self.send_request(
                VEHICLES_URL.format(server=self.server_url),
                headers=self.request_header(brand),
                params={
                    "apptimezone": self._utcdiff,
                    "appDateTime": datetime.datetime.utcnow().timestamp(),
                    "tireGuardMode": "ENABLED"},
                logfilename="vehicles_v2_{}".format(brand.value),
            )

            for vehicle_dict in response.json():
                # If vehicle already exists, just update it's state
                existing_vehicle = self.get_vehicle(vehicle_dict["vin"])
                if existing_vehicle:
                    existing_vehicle.update_state(vehicle_dict)
                else:
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
        # With MyBMW, we only have to get the vehicles list.
        self._get_vehicles()
        for listener in self._update_listeners:
            listener()

    def add_update_listener(self, listener: Callable[[], Any]) -> None:
        """Add a listener for state updates."""
        self._update_listeners.append(listener)

    @property
    def vehicles(self) -> List[ConnectedDriveVehicle]:
        """Get list of vehicle of this account"""
        return self._vehicles

    def __str__(self) -> str:
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

    @property
    def _utcdiff(self):
        return round((datetime.datetime.now() - datetime.datetime.utcnow()).seconds / 60, 0)
