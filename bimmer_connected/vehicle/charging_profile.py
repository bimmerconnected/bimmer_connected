"""Models the charging profiles of a vehicle."""

import datetime
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from bimmer_connected.vehicle.models import StrEnum, VehicleDataBase

_LOGGER = logging.getLogger(__name__)


class ChargingMode(StrEnum):
    """Charging mode of electric vehicle."""

    IMMEDIATE_CHARGING = "immediateCharging"
    DELAYED_CHARGING = "delayedCharging"


class ChargingPreferences(StrEnum):
    """Charging preferences of electric vehicle."""

    NO_PRESELECTION = "noPreSelection"
    CHARGING_WINDOW = "chargingWindow"


class TimerTypes(StrEnum):
    """Different timer types."""

    TWO_WEEKS = "twoWeeksTimer"
    ONE_WEEK = "weeklyPlanner"
    OVERRIDE_TIMER = "overrideTimer"


class ChargingWindow:
    """A charging window."""

    def __init__(self, window_dict: dict):
        self._window_dict = window_dict

    @property
    def start_time(self) -> datetime.time:
        """Start of the charging window."""
        # end of reductionOfChargeCurrent == start of charging window
        return datetime.time(int(self._window_dict["end"]["hour"]), int(self._window_dict["end"]["minute"]))

    @property
    def end_time(self) -> datetime.time:
        """End of the charging window."""
        # start of reductionOfChargeCurrent == end of charging window
        return datetime.time(int(self._window_dict["start"]["hour"]), int(self._window_dict["start"]["minute"]))


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

        if "status" not in vehicle_data or "chargingProfile" not in vehicle_data["status"]:
            if vehicle_data["capabilities"]["isChargingPlanSupported"]:
                _LOGGER.error("Unable to read data from `status.chargingProfile`.")
            return retval

        charging_profile = vehicle_data["status"]["chargingProfile"]

        retval["is_pre_entry_climatization_enabled"] = bool(charging_profile["climatisationOn"])
        retval["departure_times"] = [DepartureTimer(t) for t in charging_profile["departureTimes"]]
        retval["preferred_charging_window"] = ChargingWindow(charging_profile["reductionOfChargeCurrent"])
        retval["timer_type"] = TimerTypes(charging_profile["chargingControlType"])
        retval["charging_preferences"] = ChargingPreferences(charging_profile["chargingPreference"])
        retval["charging_mode"] = ChargingMode(charging_profile["chargingMode"])

        return retval
