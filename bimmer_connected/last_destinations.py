"""Models the charging profiles of a vehicle."""

import logging
from typing import List
from enum import Enum

from bimmer_connected.const import SERVICE_DESTINATIONS

_LOGGER = logging.getLogger(__name__)


class DestinationType(Enum):
    """Types of destinations."""
    DESTINATION = 'DESTINATION'


class Destination:
    """
    This class provides a nicer API than parsing the JSON format directly.
    """

    def __init__(self, ccm_dict: dict):
        self._ccm_dict = ccm_dict

    @property
    def latitude(self) -> float:
        """latitude of this destination."""
        return self._ccm_dict["lat"]

    @property
    def longitude(self) -> float:
        """longitude of this destination."""
        return self._ccm_dict["lon"]

    @property
    def country(self) -> str:
        """Country of this destination."""
        return int(self._ccm_dict["country"])

    @property
    def city(self) -> str:
        """City of this destination."""
        return int(self._ccm_dict["city"])

    @property
    def street(self) -> str:
        """Street of this destination."""
        return int(self._ccm_dict["street"])

    @property
    def type(self) -> DestinationType:
        """Type of this destination."""
        return DestinationType(self._ccm_dict["type"])

    @property
    def created_at(self) -> str:
        """Date of creation of this destination."""
        return int(self._ccm_dict["createdAt"])


def backend_parameter(func):
    """Decorator for parameters reading data from the backend.

    Errors are handled in a default way.
    """
    def _func_wrapper(self: 'LastDestinations', *args, **kwargs):
        # pylint: disable=protected-access
        if self._state.attributes[SERVICE_DESTINATIONS] is None:
            raise ValueError('No data available for vehicle destinations!')
        try:
            return func(self, *args, **kwargs)
        except KeyError:
            _LOGGER.debug('No data available for attribute %s!', str(func))
            return None
    return _func_wrapper


class LastDestinations:  # pylint: disable=too-many-public-methods
    """Models the last destinations of a vehicle."""

    def __init__(self, state):
        """Constructor."""
        self._state = state

    @property
    @backend_parameter
    def attributes(self) -> dict:
        """Retrieve all attributes from the sever.

        This does not parse the results in any way.
        """
        return self._state.attributes[SERVICE_DESTINATIONS]

    def __getattr__(self, item):
        """Generic get function for all backend attributes."""
        return self._state.attributes[SERVICE_DESTINATIONS][item]

    @property
    @backend_parameter
    def last_destinations(self) -> List[Destination]:
        """Get the list of last destinations."""
        destinations_list = []
        for dest in self._state.attributes[SERVICE_DESTINATIONS]:
            destinations_list.append(Destination(dest))