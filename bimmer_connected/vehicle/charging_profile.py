"""Models the charging profiles of a vehicle."""

import datetime
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from bimmer_connected.const import ATTR_CHARGING_SETTINGS, ATTR_STATE
from bimmer_connected.models import StrEnum, VehicleDataBase

_LOGGER = logging.getLogger(__name__)


class ChargingMode(StrEnum):
    """Charging mode of electric vehicle."""

    IMMEDIATE_CHARGING = "IMMEDIATE_CHARGING"
    DELAYED_CHARGING = "DELAYED_CHARGING"
    NO_ACTION = "NO_ACTION"
    UNKNOWN = "UNKNOWN"


MAP_CHARGING_MODE_TO_REMOTE_SERVICE = {
    ChargingMode.IMMEDIATE_CHARGING: "CHARGING_IMMEDIATELY",
    ChargingMode.DELAYED_CHARGING: "TIME_SLOT",
    ChargingMode.NO_ACTION: "NO_ACTION",
    ChargingMode.UNKNOWN: "NO_ACTION",
}


class ChargingPreferences(StrEnum):
    """Charging preferences of electric vehicle."""

    NO_PRESELECTION = "NO_PRESELECTION"
    CHARGING_WINDOW = "CHARGING_WINDOW"
    UNKNOWN = "UNKNOWN"


class TimerTypes(StrEnum):
    """Different timer types."""

    WEEKLY_PLANNER = "WEEKLY_PLANNER"
    TWO_TIMES_TIMER = "TWO_TIMES_TIMER"
    UNKNOWN = "UNKNOWN"


MAP_TIMER_TYPES_TO_REMOTE_SERVICE = {
    TimerTypes.WEEKLY_PLANNER: "WEEKLY_DEPARTURE_TIMER",
    TimerTypes.TWO_TIMES_TIMER: "TWO_DEPARTURE_TIMER",
}


class ChargingWindow:
    """A charging window."""

    def __init__(self, window_dict: dict):
        self._window_dict = window_dict

    @property
    def start_time(self) -> datetime.time:
        """Start of the charging window."""
        if "start" not in self._window_dict:
            return datetime.time(0, 0)
        return datetime.time(int(self._window_dict["start"]["hour"]), int(self._window_dict["start"]["minute"]))

    @property
    def end_time(self) -> datetime.time:
        """End of the charging window."""
        if "end" not in self._window_dict:
            return datetime.time(0, 0)
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
class ChargingProfile(VehicleDataBase):
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

    ac_current_limit: Optional[int] = None
    """Returns the ac current limit."""

    ac_available_limits: Optional[list] = None
    """Available AC limits to be selected."""

    charging_preferences_service_pack: Optional[str] = None
    """Service Pack required for remote service format."""

    @classmethod
    def _parse_vehicle_data(cls, vehicle_data: Dict) -> Dict:
        """Parse charging data."""
        retval: Dict[str, Any] = {}
        if ATTR_STATE in vehicle_data and (charging_profile := vehicle_data[ATTR_STATE].get("chargingProfile")):
            retval["is_pre_entry_climatization_enabled"] = bool(charging_profile.get("climatisationOn", False))
            retval["departure_times"] = [DepartureTimer(t) for t in charging_profile.get("departureTimes", [])]
            retval["preferred_charging_window"] = ChargingWindow(charging_profile.get("reductionOfChargeCurrent", {}))
            retval["timer_type"] = TimerTypes(charging_profile.get("chargingControlType", "UNKNOWN"))
            retval["charging_preferences"] = ChargingPreferences(charging_profile.get("chargingPreference", "UNKNOWN"))
            retval["charging_mode"] = ChargingMode(charging_profile.get("chargingMode", "UNKNOWN"))
            if "acCurrentLimit" in charging_profile["chargingSettings"]:
                retval["ac_current_limit"] = charging_profile["chargingSettings"]["acCurrentLimit"]

        if charging_settings := vehicle_data.get(ATTR_CHARGING_SETTINGS):
            if "servicePack" in charging_settings:
                retval["charging_preferences_service_pack"] = charging_settings["servicePack"]
            if (
                "chargingSettingsDetail" in charging_settings
                and "acLimit" in charging_settings["chargingSettingsDetail"]
            ):
                retval["ac_available_limits"] = charging_settings["chargingSettingsDetail"]["acLimit"]["values"]
        return retval

    def format_for_remote_service(self) -> dict:
        """Format current charging profile as base to be sent to remote service."""

        return {
            "chargingMode": {
                "chargingPreference": self.charging_preferences.value,
                "endTimeSlot": self._format_time(self.preferred_charging_window.end_time),
                "startTimeSlot": self._format_time(self.preferred_charging_window.start_time),
                "type": MAP_CHARGING_MODE_TO_REMOTE_SERVICE[self.charging_mode],
                "timerChange": "NO_CHANGE",
            },
            "departureTimer": {
                "type": MAP_TIMER_TYPES_TO_REMOTE_SERVICE[self.timer_type],
                "weeklyTimers": [
                    {
                        "daysOfTheWeek": t.weekdays,
                        "id": t.timer_id,
                        "time": self._format_time(t.start_time),
                        "timerAction": t.action,
                    }
                    for t in self.departure_times
                ],
            },
            "isPreconditionForDepartureActive": self.is_pre_entry_climatization_enabled,
            "servicePack": self.charging_preferences_service_pack,
        }

    @staticmethod
    def _format_time(time: Optional[datetime.time] = None) -> str:
        if not time:
            return "0001-01-01T00:00:00.000"
        return time.strftime("0001-01-01T%H:%M:00.000")
