"""Models the charging profiles of a vehicle."""

import datetime
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from bimmer_connected.const import ATTR_STATE
from bimmer_connected.models import StrEnum, VehicleDataBase

_LOGGER = logging.getLogger(__name__)


class ChargingMode(StrEnum):
    """Charging mode of electric vehicle."""

    IMMEDIATE_CHARGING = "IMMEDIATE_CHARGING"
    DELAYED_CHARGING = "DELAYED_CHARGING"
    UNKNOWN = "UNKNOWN"


class ChargingPreferences(StrEnum):
    """Charging preferences of electric vehicle."""

    NO_PRESELECTION = "NO_PRESELECTION"
    CHARGING_WINDOW = "CHARGING_WINDOW"
    UNKNOWN = "UNKNOWN"


class TimerTypes(StrEnum):
    """Different timer types."""

    TWO_WEEKS = "TWO_WEEKS_TIMER"
    ONE_WEEK = "WEEKLY_PLANNER"
    OVERRIDE_TIMER = "OVERRIDE_TIMER"
    TWO_TIMES_TIMER = "TWO_TIMES_TIMER"
    UNKNOWN = "UNKNOWN"


class ChargingWindow:
    """A charging window."""

    def __init__(self, window_dict: dict):
        self._window_dict = window_dict

    @property
    def start_time(self) -> datetime.time:
        """Start of the charging window."""
        return datetime.time(int(self._window_dict["start"]["hour"]), int(self._window_dict["start"]["minute"]))

    @property
    def end_time(self) -> datetime.time:
        """End of the charging window."""
        return datetime.time(int(self._window_dict["end"]["hour"]), int(self._window_dict["end"]["minute"]))


class DepartureTimer:
    """A departure timer."""

    def __init__(self, timer_dict: dict):
        self._timer_dict: Dict = timer_dict

    @property
    def timer_id(self) -> Optional[int]:
        """ID of this timer."""
        return self._timer_dict.get("id")

    @property
    def start_time(self) -> Optional[datetime.time]:
        """Deperture time for this timer."""
        if "timeStamp" not in self._timer_dict:
            return None
        return datetime.time(int(self._timer_dict["timeStamp"]["hour"]), int(self._timer_dict["timeStamp"]["minute"]))

    @property
    def action(self) -> Optional[str]:
        """What does the timer do."""
        return self._timer_dict.get("action")

    @property
    def weekdays(self) -> List[str]:
        """Active weekdays for this timer."""
        return self._timer_dict.get("timerWeekDays")  # type: ignore[return-value]


@dataclass
class ChargingProfile(VehicleDataBase):  # pylint:disable=too-many-instance-attributes
    """Models the charging profile of a vehicle."""

    is_pre_entry_climatization_enabled: bool
    """Get status of pre-entry climatization."""

    timer_type: TimerTypes
    """Returns the current timer plan type."""

    departure_times: List[DepartureTimer]
    """List of timers."""

    preferred_charging_window: ChargingWindow
    """Returns the preferred charging window."""

    charging_preferences: ChargingPreferences
    """Returns the preferred charging preferences."""

    charging_mode: ChargingMode
    """Returns the preferred charging mode."""

    @classmethod
    def _parse_vehicle_data(cls, vehicle_data: Dict) -> Dict:
        """Parse doors and windows."""
        retval: Dict[str, Any] = {}

        if ATTR_STATE in vehicle_data and "chargingProfile" in vehicle_data[ATTR_STATE]:
            charging_profile = vehicle_data[ATTR_STATE]["chargingProfile"]

            retval["is_pre_entry_climatization_enabled"] = bool(charging_profile.get("climatisationOn", False))
            retval["departure_times"] = [DepartureTimer(t) for t in charging_profile.get("departureTimes", [])]
            retval["preferred_charging_window"] = ChargingWindow(charging_profile.get("reductionOfChargeCurrent", {}))
            retval["timer_type"] = TimerTypes(charging_profile.get("chargingControlType", "UNKNOWN"))
            retval["charging_preferences"] = ChargingPreferences(charging_profile.get("chargingPreference", "UNKNOWN"))
            retval["charging_mode"] = ChargingMode(charging_profile.get("chargingMode", "UNKNOWN"))

        return retval
