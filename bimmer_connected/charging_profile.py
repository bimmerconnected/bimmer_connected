"""Models the charging profiles of a vehicle."""

import logging
from typing import List
from enum import Enum

from bimmer_connected.const import SERVICE_CHARGING_PROFILE

_LOGGER = logging.getLogger(__name__)


class ChargingMode(Enum):
    """Charging mode of electric vehicle."""
    IMMEDIATE_CHARGING = 'IMMEDIATE_CHARGING'
    DELAYED_CHARGING = 'DELAYED_CHARGING'


class ChargingPreferences(Enum):
    """Charging preferences of electric vehicle."""
    NO_PRESELECTION = 'NO_PRESELECTION'
    CHARGING_WINDOW = 'CHARGING_WINDOW'


class TimerTypes(Enum):
    """Different Timer-Types."""
    TIMER_1 = 'timer1'
    TIMER_2 = 'timer2'
    TIMER_3 = 'timer3'
    OVERRIDE_TIMER = 'overrideTimer'


class ChargingWindow:
    """
    This class provides a nicer API than parsing the JSON format directly.
    """

    def __init__(self, window_dict: dict):
        self._window_dict = window_dict

    @property
    def start_time(self) -> str:
        """Start of the charging window."""
        return self._window_dict["startTime"]

    @property
    def end_time(self) -> str:
        """End of the charging window."""
        return self._window_dict["endTime"]


class ClimatizationTimer:
    """
    This class provides a nicer API than parsing the JSON format directly.
    """

    def __init__(self, clima_dict: dict):
        self._clima_dict = clima_dict

    @property
    def departure_time(self) -> str:
        """Deperture time for this timer."""
        return self._clima_dict["departureTime"]

    @property
    def timer_enabled(self) -> bool:
        """Is the timer enabled."""
        return self._clima_dict["timerEnabled"]

    @property
    def weekdays(self) -> List[str]:
        """Active weekdays for this timer."""
        return self._clima_dict["weekdays"]


def backend_parameter(func):
    """Decorator for parameters reading data from the backend.

    Errors are handled in a default way.
    """
    def _func_wrapper(self: 'ChargingProfile', *args, **kwargs):
        # pylint: disable=protected-access
        if self._state.attributes[SERVICE_CHARGING_PROFILE] is None:
            raise ValueError('No data available for vehicles charging profile!')
        try:
            return func(self, *args, **kwargs)
        except KeyError:
            _LOGGER.debug('No data available for attribute %s!', str(func))
            return None
    return _func_wrapper


class ChargingProfile:  # pylint: disable=too-many-public-methods
    """Models the charging profile of a vehicle."""

    def __init__(self, state):
        """Constructor."""
        self._state = state

    @property
    @backend_parameter
    def attributes(self) -> dict:
        """Retrieve all attributes from the sever.

        This does not parse the results in any way.
        """
        return self._state.attributes[SERVICE_CHARGING_PROFILE]

    def __getattr__(self, item):
        """Generic get function for all backend attributes."""
        return self._state.attributes[SERVICE_CHARGING_PROFILE][item]

    @property
    def available_attributes(self) -> List[str]:
        """Get the list of charging-profile attributes available for this vehicle."""
        result = ['is_pre_entry_climatization_enabled', 'pre_entry_climatization_timer',
                  'preferred_charging_window', 'charging_preferences', 'charging_mode']
        return result

    @property
    @backend_parameter
    def is_pre_entry_climatization_enabled(self) -> bool:
        """Get status of pre-entry climatization."""
        return bool(self._state.attributes[SERVICE_CHARGING_PROFILE]['climatizationEnabled'])

    @property
    @backend_parameter
    def pre_entry_climatization_timer(self) -> dict:
        """List of pre entry climatization timer messages."""
        timer_list = {}
        for timer in TimerTypes:
            try:
                timer_list[timer] = ClimatizationTimer(self._state.attributes[SERVICE_CHARGING_PROFILE][timer.value])
            except KeyError:
                _LOGGER.debug('Timer %s not found', timer.value)
        return timer_list

    @property
    @backend_parameter
    def preferred_charging_window(self) -> ChargingWindow:
        """Returns the preferred charging window."""
        return ChargingWindow(self._state.attributes[SERVICE_CHARGING_PROFILE]['preferredChargingWindow'])

    @property
    @backend_parameter
    def charging_preferences(self) -> str:
        """Returns the prefered charging preferences."""
        return ChargingPreferences(self._state.attributes[SERVICE_CHARGING_PROFILE]['chargingPreferences'])

    @property
    @backend_parameter
    def charging_mode(self) -> str:
        """Returns the prefered charging mode."""
        return ChargingMode(self._state.attributes[SERVICE_CHARGING_PROFILE]['chargingMode'])
