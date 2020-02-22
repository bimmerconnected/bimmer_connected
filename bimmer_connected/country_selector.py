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


class LoginType(Enum):
    """Login types of BMW API."""
    GLOBAL = 0
    LEGACY = 1


#: Mapping from regions to servers
_SERVER_URLS = {
    Regions.NORTH_AMERICA: {
        'login_type': LoginType.GLOBAL,
        'auth_url': 'customer.bmwgroup.com/gcdm/usa/oauth/token',
        'server': 'myc-profile.bmwusa.com',
    },
    Regions.REST_OF_WORLD: {
        'login_type': LoginType.GLOBAL,
        'auth_url': 'customer.bmwgroup.com/gcdm/oauth/token',
        'server': 'myc-profile.bmwgroup.com',
    },
    Regions.CHINA: {
        'login_type': LoginType.LEGACY,
        'auth_url': 'b2vapi.bmwgroup.cn:8592/gcdm/oauth/token',
        'server': 'b2vapi.bmwgroup.cn:8592',
    }
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
    return _SERVER_URLS[region]['server']


def get_auth_url(region: Regions) -> str:
    """Get the url of the server for the region."""
    return _SERVER_URLS[region]['auth_url']


def get_login_type(region: Regions) -> str:
    """Get the url of the server for the region."""
    return _SERVER_URLS[region]['login_type']
