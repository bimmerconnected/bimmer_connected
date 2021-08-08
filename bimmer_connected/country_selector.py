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
    Regions.NORTH_AMERICA: "login.bmwusa.com/gcdm",
    Regions.REST_OF_WORLD: "customer.bmwgroup.com/gcdm",
    Regions.CHINA: "customer.bmwgroup.cn/gcdm",
}

_GCDM_OAUTH_AUTHORIZATION = {
    Regions.NORTH_AMERICA: {
        "token": {
            "Authorization": ("Basic NTQzOTRhNGItYjZjMS00NWZlLWI3YjItOGZkM2FhOTI1M2F"
                              "hOmQ5MmYzMWMwLWY1NzktNDRmNS1hNzdkLTk2NmY4ZjAwZTM1MQ=="),
            "code_verifier": "KDarcVUpgymBDCgHDH0PwwMfzycDxu1joeklioOhwXA",
        },
        "authenticate": {
            "client_id": "54394a4b-b6c1-45fe-b7b2-8fd3aa9253aa",
            "state": "rgastJbZsMtup49-Lp0FMQ",
        },
    },
    Regions.REST_OF_WORLD: {
        "token": {
            "Authorization": ("Basic MzFjMzU3YTAtN2ExZC00NTkwLWFhOTktMzNiOTcyNDRkMDQ"
                              "4OmMwZTMzOTNkLTcwYTItNGY2Zi05ZDNjLTg1MzBhZjY0ZDU1Mg=="),
            "code_verifier": "7PsmfPS5MpaNt0jEcPpi-B7M7u0gs1Nzw6ex0Y9pa-0",
        },
        "authenticate": {
            "client_id": "31c357a0-7a1d-4590-aa99-33b97244d048",
            "state": "cEG9eLAIi6Nv-aaCAniziE_B6FPoobva3qr5gukilYw",
        },
    },
    Regions.CHINA: {
        "token": {
            "Authorization": ("Basic MzFjMzU3YTAtN2ExZC00NTkwLWFhOTktMzNiOTcyNDRkMDQ"
                              "4OmMwZTMzOTNkLTcwYTItNGY2Zi05ZDNjLTg1MzBhZjY0ZDU1Mg=="),
            "code_verifier": "",
        },
        "authenticate": {
            "client_id": None,
            "state": None,
        },
    },
}


def valid_regions() -> List[str]:
    """Get list of valid regions as strings."""
    return [region.name.lower() for region in Regions]


def get_region_from_name(name: str) -> Regions:
    """Get a region for a string.

    This function is not case-sensitive.
    """
    for region in Regions:
        if name.lower() == region.name.lower():
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
