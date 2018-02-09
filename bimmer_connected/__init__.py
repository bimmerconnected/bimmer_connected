"""Library to read data from the BMW Connected Drive portal.

Disclaimer:
This library is not affiliated with or endorsed by BMW Group.
"""
import string
import random
import datetime
import logging
import urllib
import requests

AUTH_URL = 'https://customer.bmwgroup.com/gcdm/oauth/authenticate'
VEHICLE_URL = 'https://www.bmw-connecteddrive.de/api/vehicle'

_LOGGER = logging.getLogger(__name__)


def none_on_keyerror(func):
    """decorator to return None when catching a KeyError."""
    def _func_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyError:
            return None
    return _func_wrapper


class BimmerConnected(object):
    """Read data for a BMW from the Connected Driver portal."""

    def __init__(self, vin: str, username: str, password: str) -> None:
        self._vin = vin
        self._username = username
        self._password = password
        self._oauth_token = None
        self._token_expiration = None
        self.attributes = None

    def _get_oauth_token(self) -> None:
        """Get a new auth token from the server."""
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
        response = requests.post(AUTH_URL, data=data, headers=headers, allow_redirects=False)

        if response.status_code != 302:
            raise IOError('Unknown status code {}'.format(response.status_code))

        url_with_token = urllib.parse.parse_qs(response.headers['Location'])
        self._oauth_token = url_with_token['access_token'][0]
        expiration_time = int(url_with_token['expires_in'][0])
        self._token_expiration = datetime.datetime.now() + datetime.timedelta(seconds=expiration_time)
        _LOGGER.debug('got new token %s with expiration date %s', self._oauth_token, self._token_expiration)

    def update_data(self) -> None:
        """Read new status data from the server."""
        _LOGGER.debug('requesting new data from connected drive')
        self._get_oauth_token()
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(self._oauth_token)
            }

        response = requests.get(VEHICLE_URL+'/dynamic/v1/{}'.format(self._vin),
                                headers=headers, allow_redirects=True)

        if response.status_code != 200:
            raise IOError('Unknown status code {}'.format(response.status_code))

        attributes = response.json()['attributesMap']
        if attributes['head_unit'] != 'NBTEvo':
            _LOGGER.warning('This library is not yet tested with this type of head unit: %s. If you experience any'
                            'problems open an issue at: '
                            'https://github.com/ChristianKuehnel/bimmer_connected/issues '
                            'And provide the logged attributes below.',
                            attributes['head_unit'])
            _LOGGER.warning(attributes)
        self.attributes = attributes
        _LOGGER.debug('received new data from connected drive')

    @staticmethod
    def _random_string(length):
        """Create a random string of a given length."""
        return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))

    @property
    @none_on_keyerror
    def timestamp(self) -> datetime.datetime:
        """Get the timestamp when the data was recorded."""
        return datetime.datetime.fromtimestamp(int(self.attributes['updateTime_converted_timestamp'])/1000)

    @property
    @none_on_keyerror
    def gps_latitude(self) -> float:
        """Get the last known position of the vehicle."""
        return float(self.attributes['gps_lat'])

    @property
    @none_on_keyerror
    def gps_longitude(self) -> float:
        """Get the last known position of the vehicle."""
        return float(self.attributes['gps_lng'])

    @property
    @none_on_keyerror
    def unit_of_length(self) -> str:
        """Get the unit in which the length is measured."""
        return self.attributes['unitOfLength']

    @property
    @none_on_keyerror
    def mileage(self) -> float:
        """Get the mileage of the vehicle."""
        return float(self.attributes['mileage'])

    @property
    @none_on_keyerror
    def remaining_range_fuel(self) -> float:
        """Get the remaining range of the vehicle on fuel."""
        return float(self.attributes['beRemainingRangeFuel'])

    @property
    @none_on_keyerror
    def remaining_fuel(self) -> float:
        """Get the remaining fuel of the vehicle.

        Not sure if the unit is always in liters."""
        return float(self.attributes['remaining_fuel'])
