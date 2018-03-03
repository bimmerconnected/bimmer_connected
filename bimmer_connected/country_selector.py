"""Get the right url for the different countries."""
import logging
import requests
from bimmer_connected.const import COUNTRY_SELECTION_URL, AUTH_URL_DICT, AUTH_URL_REST_OF_WORLD

_LOGGER = logging.getLogger(__name__)


class CountrySelector(object):  # pylint: disable=too-few-public-methods
    """Get the right url for the different countries."""

    # cache the reply from the server
    _countries = None

    def get_url(self, country: str) -> str:
        """Get the web service url for a country.

        :param country: country to get the list for. For a list of valid
                        countries, check https://www.bmw-connecteddrive.com
                        Use the name of the countries exactly as on the website.
        """
        if self._countries is None:
            response = self._get_json_list()
            self._countries = self._parse_response(response)
        if country not in self._countries:
            raise ValueError('Unknown country "{}". The list of valid countries can be seen on '
                             'https://www.bmw-connecteddrive.com'.format(country))
        result = self._countries[country]
        _LOGGER.debug('the url for country %s is %s', country, result)
        return result

    @staticmethod
    def get_authentication_url(country: str) -> str:
        """Get the authentication url for the country."""
        if country in AUTH_URL_DICT:
            return AUTH_URL_DICT[country]
        return AUTH_URL_REST_OF_WORLD

    @staticmethod
    def _get_json_list() -> dict:
        """Get the current country list from the server."""
        response = requests.get(COUNTRY_SELECTION_URL)
        if response.status_code != 200:
            msg = 'Error reading the country selection list. HTTP status {}'.format(response.status_code)
            _LOGGER.error(msg)
            _LOGGER.debug(response.headers)
            _LOGGER.debug(response.text)
            raise IOError(msg)
        return response.json()

    @staticmethod
    def _parse_response(response: dict) -> dict:
        """parse the response from the server and create a dictionary of country and url."""
        countries = []
        for _, groups in response['countryData'].items():
            for group in groups:
                countries.extend(group['countries'])

        result = dict()
        for country in countries:
            result[country['name']] = country['link'].rstrip('/')
        return result
