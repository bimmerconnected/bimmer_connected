"""Models the state of the vehicle tires."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from bimmer_connected.const import ATTR_STATE
from bimmer_connected.models import VehicleDataBase


class TireState:
    """A tire of the vehicle."""

    def __init__(self, status: Dict, details: Optional[Dict] = None):
        self.current_pressure: Optional[int] = status.get("currentPressure")
        self.target_pressure: Optional[int] = status.get("targetPressure")
        self.season: Optional[int] = None
        self.manufacturing_week: Optional[datetime] = None

        if details:
            self.season = details.get("season")
            if details.get("manufacturingWeek"):
                iso_string = f"20{details['manufacturingWeek'] % 100}." f"{int(details['manufacturingWeek'] / 100)}.1"
                self.manufacturing_week = datetime.strptime(
                    iso_string,
                    "%G.%V.%u",
                )


@dataclass
class Tires(VehicleDataBase):
    """Provides an accessible version of `state.tireState`."""

    front_left: TireState
    """Front left tire info."""

    front_right: TireState
    """Front right tire info."""

    rear_left: TireState
    """Rear left tire info."""

    rear_right: TireState
    """Rear right tire info."""

    @classmethod
    def _parse_vehicle_data(cls, vehicle_data: Dict) -> Dict:
        """Parse tire status."""
        retval: Dict[str, Any] = {}

        if ATTR_STATE in vehicle_data:
            if "tireState" in vehicle_data[ATTR_STATE]:
                retval["front_left"] = TireState(**vehicle_data[ATTR_STATE]["tireState"]["frontLeft"])
                retval["front_right"] = TireState(**vehicle_data[ATTR_STATE]["tireState"]["frontRight"])
                retval["rear_left"] = TireState(**vehicle_data[ATTR_STATE]["tireState"]["rearLeft"])
                retval["rear_right"] = TireState(**vehicle_data[ATTR_STATE]["tireState"]["rearRight"])

        return retval
