"""Get the right url for the different countries."""
from enum import Enum
import logging

_LOGGER = logging.getLogger(__name__)


class Regions(Enum):
    NORTH_AMERICA = 0,
    REST_OF_WORLD = 1


#: Mapping from regions to servers
SERVER_URLS = {
    Regions.NORTH_AMERICA: 'b2vapi.bmwgroup.us',
    Regions.REST_OF_WORLD: 'b2vapi.bmwgroup.com',
}


class CountrySelector(object):  # pylint: disable=too-few-public-methods
    """Get the right url for the different countries."""

    # cache the reply from the server
    _countries = None

    def get_server_url(self, region: Regions) -> str:
        return SERVER_URLS[region]
