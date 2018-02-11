"""Get the right url for the different countries."""
import logging
import requests

_LOGGER = logging.getLogger(__name__)

COUNTRY_SELECTION_URL = 'https://www.bmw-connecteddrive.com/cms/default/default/country-selection.json'


class CountrySelector(object):  # pylint: disable=too-few-public-methods
    """Get the right url for the different countries."""

    # cache the reply from the server
    _countries = None

    def get_url(self, country: str):
        """Get the url for a country."""
        if self._countries is None:
            response = self._get_json_list()
            self._countries = self._parse_response(response)
        result = self._countries[country]
        _LOGGER.debug('the url for country %s is %s', country, result)
        return result

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
