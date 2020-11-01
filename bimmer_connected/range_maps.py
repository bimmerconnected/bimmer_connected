"""Models the range maps of a vehicle."""

import logging
from typing import List
from enum import Enum

from bimmer_connected.const import SERVICE_RANGEMAP

_LOGGER = logging.getLogger(__name__)


class RangeMapServices(Enum):
    """Range map services."""
    POLYGON = 'RANGE_POLYGON'
    CIRCLE = 'RANGE_CIRCLE'


class RangeMapType(Enum):
    """Range map types."""
    ECO_PRO_PLUS = 'ECO_PRO_PLUS'
    COMFORT = 'COMFORT'


class RangeMapQuality(Enum):
    """Range map types."""
    AVERAGE = 'AVERAGE'


class MapPoint:
    """
    This class provides a nicer API than parsing the JSON format directly.
    """

    def __init__(self, mp_dict: dict):
        self._mp_dict = mp_dict

    @property
    def latitude(self) -> float:
        """latitude of this point."""
        return float(self._mp_dict["lat"])

    @property
    def longitude(self) -> float:
        """longitude of this point."""
        return float(self._mp_dict["lon"])


class RangeMap:
    """
    This class provides a nicer API than parsing the JSON format directly.
    """

    def __init__(self, range_dict: dict):
        self._range_dict = range_dict

    @property
    def range_map_type(self) -> RangeMapType:
        """Type of the range map."""
        return RangeMapType(self._range_dict["type"])

    @property
    def polyline(self) -> List[MapPoint]:
        """polylines of this range map."""
        pol_list = []
        for map_point in self._range_dict["polyline"]:
            pol_list.append(MapPoint(map_point))
        return pol_list


def backend_parameter(func):
    """Decorator for parameters reading data from the backend.

    Errors are handled in a default way.
    """
    def _func_wrapper(self: 'RangeMaps', *args, **kwargs):
        # pylint: disable=protected-access
        if self._state.attributes[SERVICE_RANGEMAP] is None:
            raise ValueError('No data available for range maps!')
        try:
            return func(self, *args, **kwargs)
        except KeyError:
            _LOGGER.debug('No data available for attribute %s!', str(func))
            return None
    return _func_wrapper


class RangeMaps:  # pylint: disable=too-many-public-methods
    """Models the range maps of a vehicle."""

    def __init__(self, state):
        """Constructor."""
        self._state = state

    @property
    @backend_parameter
    def attributes(self) -> dict:
        """Retrieve all attributes from the sever.

        This does not parse the results in any way.
        """
        return self._state.attributes[SERVICE_RANGEMAP]

    def __getattr__(self, item):
        """Generic get function for all backend attributes."""
        return self._state.attributes[SERVICE_RANGEMAP][item]

    @property
    @backend_parameter
    def range_map_quality(self) -> RangeMapQuality:
        """Type of the range map."""
        return RangeMapQuality(self._state.attributes[SERVICE_RANGEMAP]["quality"])

    @property
    @backend_parameter
    def range_map_center(self) -> RangeMapQuality:
        """Type of the range map."""
        return MapPoint(self._state.attributes[SERVICE_RANGEMAP]["center"])

    @property
    @backend_parameter
    def range_maps(self) -> List[RangeMap]:
        """Get the list range maps."""
        range_maps_list = []
        for dest in self._state.attributes[SERVICE_RANGEMAP]["rangemaps"]:
            range_maps_list.append(RangeMap(dest))
        return range_maps_list
