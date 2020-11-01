"""Models the efficiency of a vehicle."""

import logging
from typing import List

from bimmer_connected.const import SERVICE_EFFICIENCY

_LOGGER = logging.getLogger(__name__)


class LastTrip:
    """Last Trip.

    This class provides a nicer API than parsing the JSON format directly.
    """

    def __init__(self, trip_dict: dict):
        self._trip_dict = trip_dict

    @property
    def name(self) -> str:
        """Name."""
        return self._trip_dict["name"]

    @property
    def unit(self) -> str:
        """Unit."""
        return self._trip_dict["unit"]

    @property
    def last_trip(self) -> str:
        """Last Trip."""
        return self._trip_dict["lastTrip"]


def backend_parameter_life_time(func):
    """Decorator for parameters reading data from the backend.

    Errors are handled in a default way.
    """
    def _func_wrapper(self: 'LifeTime', *args, **kwargs):
        # pylint: disable=protected-access
        try:
            return func(self, *args, **kwargs)
        except KeyError:
            _LOGGER.debug('No data available for attribute %s!', str(func))
            return None
    return _func_wrapper


class LifeTime:
    """Life Time.

    This class provides a nicer API than parsing the JSON format directly.
    """

    def __init__(self, time_dict: dict):
        self._time_dict = time_dict

    @property
    @backend_parameter_life_time
    def name(self) -> str:
        """Name."""
        return self._time_dict["name"]

    @property
    @backend_parameter_life_time
    def unit(self) -> str:
        """Unit."""
        return self._time_dict["unit"]

    @property
    @backend_parameter_life_time
    def life_time(self) -> str:
        """Life Time."""
        return self._time_dict["lifeTime"]


class Characteristic:
    """Characteristic.

    This class provides a nicer API than parsing the JSON format directly.
    """

    def __init__(self, char_dict: dict):
        self._char_dict = char_dict

    @property
    def characteristic(self) -> str:
        """Characteristic."""
        return self._char_dict["characteristic"]

    @property
    def quantity(self) -> int:
        """Quantity."""
        return int(self._char_dict["quantity"])


def backend_parameter(func):
    """Decorator for parameters reading data from the backend.

    Errors are handled in a default way.
    """
    def _func_wrapper(self: 'Efficiency', *args, **kwargs):
        # pylint: disable=protected-access
        if self._state.attributes[SERVICE_EFFICIENCY] is None:
            raise ValueError('No data available for vehicles efficiency!')
        try:
            return func(self, *args, **kwargs)
        except KeyError:
            _LOGGER.debug('No data available for attribute %s!', str(func))
            return None
    return _func_wrapper


class Efficiency:  # pylint: disable=too-many-public-methods
    """Models the navigation of a vehicle."""

    def __init__(self, state):
        """Constructor."""
        self._state = state

    @property
    @backend_parameter
    def attributes(self) -> dict:
        """Retrieve all attributes from the sever.

        This does not parse the results in any way.
        """
        return self._state.attributes[SERVICE_EFFICIENCY]

    def __getattr__(self, item):
        """Generic get function for all backend attributes."""
        return self._state.attributes[SERVICE_EFFICIENCY][item]

    @property
    @backend_parameter
    def model_type(self) -> str:
        """Returns the model type."""
        return self._state.attributes[SERVICE_EFFICIENCY]['modelType']

    @property
    @backend_parameter
    def efficiency_quotient(self) -> int:
        """Returns the efficiency quotient."""
        return int(self._state.attributes[SERVICE_EFFICIENCY]['efficiencyQuotient'])

    @property
    @backend_parameter
    def last_trip_list(self) -> List[LastTrip]:
        """Returns the list of last trips."""
        ret_list = []
        last_trip_list = self._state.attributes[SERVICE_EFFICIENCY].get('lastTripList', [])
        for trip in last_trip_list:
            ret_list.append(LastTrip(trip))
        return ret_list

    @property
    @backend_parameter
    def life_time_list(self) -> List[LifeTime]:
        """Returns the life time list."""
        ret_list = []
        last_time_list = self._state.attributes[SERVICE_EFFICIENCY].get('lifeTimeList', [])
        for time in last_time_list:
            ret_list.append(LifeTime(time))
        return ret_list

    @property
    @backend_parameter
    def characteristic_list(self) -> List[Characteristic]:
        """Returns the characteristic list."""
        ret_list = []
        characteristic_list = self._state.attributes[SERVICE_EFFICIENCY].get('characteristicList', [])
        for characteristic in characteristic_list:
            ret_list.append(Characteristic(characteristic))
        return ret_list
