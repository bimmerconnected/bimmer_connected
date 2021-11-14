"""Models the charging profiles of a vehicle."""

import logging
from typing import TYPE_CHECKING, List
from enum import Enum

from bimmer_connected.utils import SerializableBaseClass

if TYPE_CHECKING:
    from bimmer_connected.vehicle_status import VehicleStatus

_LOGGER = logging.getLogger(__name__)


class ChargingMode(str, Enum):
    """Charging mode of electric vehicle."""
    IMMEDIATE_CHARGING = 'immediateCharging'
    DELAYED_CHARGING = 'delayedCharging'


class ChargingPreferences(str, Enum):
    """Charging preferences of electric vehicle."""
    NO_PRESELECTION = 'noPreSelection'
    CHARGING_WINDOW = 'chargingWindow'


class TimerTypes(str, Enum):
    """Different Timer-Types."""
    TWO_WEEKS = 'twoWeeksTimer'
    ONE_WEEK = 'weeklyPlanner'
    OVERRIDE_TIMER = 'overrideTimer'


class ChargingWindow(SerializableBaseClass):
    """
    This class provides a nicer API than parsing the JSON format directly.
    """

    def __init__(self, window_dict: dict):
        self._window_dict = window_dict

    @property
    def start_time(self) -> str:
        """Start of the charging window."""
        # end of reductionOfChargeCurrent == start of charging window
        return "{}:{}".format(
            str(self._window_dict["end"]["hour"]).zfill(2),
            str(self._window_dict["end"]["minute"]).zfill(2),
        )

    @property
    def end_time(self) -> str:
        """End of the charging window."""
        # start of reductionOfChargeCurrent == end of charging window
        return "{}:{}".format(
            str(self._window_dict["start"]["hour"]).zfill(2),
            str(self._window_dict["start"]["minute"]).zfill(2),
        )


class DepartureTimer(SerializableBaseClass):
    """
    This class provides a nicer API than parsing the JSON format directly.
    """

    def __init__(self, timer_dict: dict):
        self._timer_dict = timer_dict

    @property
    def timer_id(self) -> int:
        """ID of this timer."""
        return self._timer_dict.get("id")

    @property
    def start_time(self) -> str:
        """Deperture time for this timer."""
        if "timeStamp" not in self._timer_dict:
            return None
        return "{}:{}".format(
            str(self._timer_dict["timeStamp"]["hour"]).zfill(2),
            str(self._timer_dict["timeStamp"]["minute"]).zfill(2),
        )

    @property
    def action(self) -> bool:
        """What does the timer do."""
        return self._timer_dict.get("action")

    @property
    def weekdays(self) -> List[str]:
        """Active weekdays for this timer."""
        return self._timer_dict.get("timerWeekDays")


def backend_parameter(func):
    """Decorator for parameters reading data from the backend.

    Errors are handled in a default way.
    """
    def _func_wrapper(self: 'ChargingProfile', *args, **kwargs):
        # pylint: disable=protected-access
        if self.charging_profile is None:
            raise ValueError('No data available for vehicles charging profile!')
        try:
            return func(self, *args, **kwargs)
        except KeyError:
            _LOGGER.debug('No data available for attribute %s!', str(func))
            return None
    return _func_wrapper


class ChargingProfile(SerializableBaseClass):  # pylint: disable=too-many-public-methods
    """Models the charging profile of a vehicle."""

    def __init__(self, status: "VehicleStatus"):
        """Constructor."""
        self.charging_profile = status.status["chargingProfile"]

    def __getattr__(self, item):
        """Generic get function for all backend attributes."""
        return self.charging_profile[item]

    @property
    @backend_parameter
    def is_pre_entry_climatization_enabled(self) -> bool:
        """Get status of pre-entry climatization."""
        return bool(self.charging_profile['climatisationOn'])

    @property
    @backend_parameter
    def timer(self) -> dict:
        """List of timer messages."""
        timer_list = {}
        for timer_dict in self.charging_profile["departureTimes"]:
            curr_timer = DepartureTimer(timer_dict)
            timer_list[curr_timer.timer_id] = curr_timer
        return timer_list

    @property
    @backend_parameter
    def preferred_charging_window(self) -> ChargingWindow:
        """Returns the preferred charging window."""
        return ChargingWindow(self.charging_profile['reductionOfChargeCurrent'])

    @property
    @backend_parameter
    def charging_preferences(self) -> str:
        """Returns the prefered charging preferences."""
        return ChargingPreferences(self.charging_profile['chargingPreference'])

    @property
    @backend_parameter
    def charging_mode(self) -> str:
        """Returns the prefered charging mode."""
        return ChargingMode(self.charging_profile['chargingMode'])
