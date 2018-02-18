"""Library to read data from the BMW Connected Drive portal.

The library bimmer_connected provides a Python interface to interact
with the BMW Connected Drive web service. It allows you to read
the current state of the vehicle and also trigger remote services.

Disclaimer:
This library is not affiliated with or endorsed by BMW Group.
"""
import string
import random
import datetime
import logging
import urllib
import os
from threading import Lock
import requests

from bimmer_connected.country_selector import CountrySelector
from bimmer_connected.vehicle import ConnectedDriveVehicle

AUTH_URL = 'https://customer.bmwgroup.com/gcdm/oauth/authenticate'
LIST_VEHICLES_URL = '{server}/api/me/vehicles/v2'

_LOGGER = logging.getLogger(__name__)


class ConnectedDriveAccount(object):  # pylint: disable=too-many-instance-attributes
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
    def __init__(self, username: str, password: str, country: str, log_responses: str = None) -> None:
        self._country = country
        self._server_url = None
        self._username = username
        self._password = password
        self._oauth_token = None
        self._token_expiration = None
        self._log_responses = log_responses
        #: list of vehicles associated with this account.
        self.vehicles = []
        self._lock = Lock()

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
            }

            # we really need all of these parameters
            values = {
                'username': self._username,
                'password': self._password,
                # not sure what this id really means, random numbers do no work here.
                'client_id': 'dbf0a542-ebd1-4ff0-a9a7-55172fbfce35',
                'redirect_uri': 'https://www.bmw-connecteddrive.com/app/default/static/external-dispatch.html',
                'response_type': 'token',
                'scope': 'authenticate_user fupo',
                'state': self._random_string(79)
            }

            data = urllib.parse.urlencode(values)
            response = self.send_request(AUTH_URL, data=data, headers=headers, allow_redirects=False,
                                         expected_response=302, post=True)

            url_with_token = urllib.parse.parse_qs(response.headers['Location'])
            self._oauth_token = url_with_token['access_token'][0]
            expiration_time = int(url_with_token['expires_in'][0])
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

    def send_request(self, url: str, data=None, headers=None, expected_response=200, post=False, allow_redirects=True):
        """Send an http request to the server.

        If the http headers are not set, default headers are generated.
        You can choose if you want a GET or POST request.
        """
        if headers is None:
            headers = self.request_header

        if post:
            response = requests.post(url, headers=headers, data=data, allow_redirects=allow_redirects)
        else:
            response = requests.get(url, headers=headers, data=data, allow_redirects=allow_redirects)

        if response.status_code != expected_response:
            msg = 'Unknown status code {}, expected {}'.format(response.status_code, expected_response)
            _LOGGER.error(msg)
            _LOGGER.error(response.text)
            raise IOError(msg)
        self._log_response_to_file(response, url)
        return response

    def _log_response_to_file(self, response: requests.Response, url: str) -> None:
        """If a log path is set, log all resonses to a file"""
        if self._log_responses is None:
            return

        replacements = [
            ('http://', ''),
            ('https://', ''),
            ('/', '_'),
        ]

        base_name = url.lower()
        for replacement in replacements:
            base_name = base_name.replace(replacement[0], replacement[1])

        with open(os.path.join(self._log_responses, '{}_headers.json'.format(base_name)), 'w') as logfile:
            logfile.write(repr(response.headers))

        with open(os.path.join(self._log_responses, '{}_data.json'.format(base_name)), 'w') as logfile:
            logfile.write(response.text)

    @staticmethod
    def _random_string(length):
        """Create a random string of a given length."""
        return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))

    @property
    def server_url(self) -> str:
        """Get the url of the server for this country."""
        if self._server_url is None:
            country_sel = CountrySelector()
            self._server_url = country_sel.get_url(self._country)
        return self._server_url

    def _get_vehicles(self):
        """Retrieve list of vehicle for the account."""
        _LOGGER.debug('Getting vehicle list')
        self._get_oauth_token()
        response = self.send_request(LIST_VEHICLES_URL.format(server=self.server_url), headers=self.request_header)

        for vehicle_dict in response.json():
            self.vehicles.append(ConnectedDriveVehicle(self, vehicle_dict))

    def get_vehicle(self, vin: str) -> ConnectedDriveVehicle:
        """Get vehicle with given VIN.

        :param vin: VIN of the vehicle you want to get.
        :return: Returns None if no such vehicle is found.
        """
        for car in self.vehicles:
            if car.vin == vin:
                return car
        return None

    def update_vehicle_states(self) -> None:
        """Update the state of all vehicles."""
        for car in self.vehicles:
            car.update_state()
