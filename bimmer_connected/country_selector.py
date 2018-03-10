"""Get the right url for the different countries."""
from enum import Enum
import logging
from typing import List

_LOGGER = logging.getLogger(__name__)


class Regions(Enum):
    """Regions of the world with separate servers."""
    NORTH_AMERICA = 0
    CHINA = 1
    REST_OF_WORLD = 2


#: Mapping from regions to servers
_SERVER_URLS = {
    Regions.NORTH_AMERICA: 'b2vapi.bmwgroup.us',
    Regions.REST_OF_WORLD: 'b2vapi.bmwgroup.com',
    Regions.CHINA: 'b2vapi.bmwgroup.cn:8592'
}


def valid_regions() -> List[str]:
    """Get list of valid regions as strings."""
    return [k.lower() for k in Regions.__members__.keys()]


def get_region_from_name(name: str) -> Regions:
    """Get a region for a string.

    This function is not case-sensitive.
    """
    for region_name, region in Regions.__members__.items():
        if name.lower() == region_name.lower():
            return region
    raise ValueError('Unknown region {}. Valid regions are: {}'.format(
        name,
        ','.join(valid_regions())))


def get_server_url(region: Regions) -> str:
    """Get the url of the server for the region."""
    return _SERVER_URLS[region]
