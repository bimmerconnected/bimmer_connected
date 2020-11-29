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
    Regions.NORTH_AMERICA: "b2vapi.bmwgroup.us",
    Regions.REST_OF_WORLD: "b2vapi.bmwgroup.com",
    Regions.CHINA: "b2vapi.bmwgroup.cn:8592",
}

#: Mapping from regions to servers
_GCDM_OAUTH_ENDPOINTS = {
    Regions.NORTH_AMERICA: "b2vapi.bmwgroup.us/gcdm",
    Regions.REST_OF_WORLD: "customer.bmwgroup.com/gcdm",
    Regions.CHINA: "customer.bmwgroup.cn/gcdm",
}

_GCDM_OAUTH_AUTHORIZATION = {
    Regions.NORTH_AMERICA: {
        "Authorization": ("Basic ZDc2NmI1MzctYTY1NC00Y2JkLWEzZGMtMGNhNTY3MmQ3Zjh"
                          "kOjE1ZjY5N2Y2LWE1ZDUtNGNhZC05OWQ5LTNhMTViYzdmMzk3Mw==")
    },
    Regions.REST_OF_WORLD: {
        "Authorization": ("Basic ZDc2NmI1MzctYTY1NC00Y2JkLWEzZGMtMGNhNTY3MmQ3Zjh"
                          "kOjE1ZjY5N2Y2LWE1ZDUtNGNhZC05OWQ5LTNhMTViYzdmMzk3Mw==")
    },
    Regions.CHINA: {
        "Authorization": ("Basic blF2NkNxdHhKdVhXUDc0eGYzQ0p3VUVQOjF6REh4NnVuNGN"
                          "EanliTEVOTjNreWZ1bVgya0VZaWdXUGNRcGR2RFJwSUJrN3JPSg==")
    },
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
    raise ValueError(
        "Unknown region {}. Valid regions are: {}".format(
            name, ",".join(valid_regions())
        )
    )


def get_server_url(region: Regions) -> str:
    """Get the url of the server for the region."""
    return _SERVER_URLS[region]


def get_gcdm_oauth_endpoint(region: Regions) -> str:
    """Get the url of the server for the region."""
    return _GCDM_OAUTH_ENDPOINTS[region]


def get_gcdm_oauth_authorization(region: Regions) -> str:
    """Get the url of the server for the region."""
    return _GCDM_OAUTH_AUTHORIZATION[region]
