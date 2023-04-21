"""Models the state of the vehicle tires."""

import datetime
from dataclasses import dataclass
from typing import Any, Dict, Optional

from bimmer_connected.const import ATTR_STATE
from bimmer_connected.models import StrEnum, VehicleDataBase


class ClimateActivityState(StrEnum):
    """Possible AC states."""

    COOLING = "COOLING"
    HEATING = "HEATING"
    INACTIVE = "INACTIVE"
    STANDBY = "STANDBY"
    UNKNOWN = "UNKNOWN"


@dataclass
class Climate(VehicleDataBase):
    """Provides an accessible version of `state.climateControlState`."""

    activity: ClimateActivityState = ClimateActivityState.UNKNOWN
    """Current climate activity state."""

    activity_end_time_no_tz: Optional[datetime.datetime] = None
    """Climatization end time w/o timezone."""

    account_timezone: datetime.timezone = datetime.timezone.utc

    @property
    def is_climate_on(self) -> bool:
        """Return True if climatization is active."""
        return self.activity in [ClimateActivityState.COOLING, ClimateActivityState.HEATING]

    @property
    def activity_end_time(self) -> Optional[datetime.datetime]:
        """Climatization end time."""
        if self.activity_end_time_no_tz:
            return self.activity_end_time_no_tz.astimezone(self.account_timezone)
        return None

    @classmethod
    def _parse_vehicle_data(cls, vehicle_data: Dict) -> Dict:
        """Parse tire status."""
        retval: Dict[str, Any] = {}

        if ATTR_STATE in vehicle_data:
            if "climateControlState" in vehicle_data[ATTR_STATE]:
                retval["activity"] = ClimateActivityState(vehicle_data[ATTR_STATE]["climateControlState"]["activity"])
                retval["activity_end_time_no_tz"] = (
                    (
                        datetime.datetime.now()
                        + datetime.timedelta(
                            seconds=int(vehicle_data[ATTR_STATE]["climateControlState"]["remainingSeconds"])
                        )
                    )
                    if "remainingSeconds" in vehicle_data[ATTR_STATE]["climateControlState"]
                    else None
                )

        return retval
