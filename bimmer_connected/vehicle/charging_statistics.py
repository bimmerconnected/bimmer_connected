"""Models the charging statistics."""

from dataclasses import dataclass
from typing import Any, Dict

from bimmer_connected.const import ATTR_STATE
from bimmer_connected.models import VehicleDataBase


@dataclass
class ChargingStatistics(VehicleDataBase):
    """Provides an accessible version of `charging_statistics`."""

    charging_session_timeperiod: str
    """Month of session statistics."""

    charging_session_count: int
    """Total number of charging sessions."""

    total_energy_charged: int
    """How much energy charged."""

    @classmethod
    def _parse_vehicle_data(cls, vehicle_data: Dict) -> Dict:
        """Parse charging statistics."""
        retval: Dict[str, Any] = {}

        if ATTR_STATE in vehicle_data:
            retval["charging_session_timeperiod"] = vehicle_data.get("charging_statistics", {}).get("description")
            retval["charging_session_count"] = (
                vehicle_data.get("charging_statistics", {}).get("statistics", {}).get("numberOfChargingSessions")
            )
            retval["total_energy_charged"] = (
                vehicle_data.get("charging_statistics", {}).get("statistics", {}).get("totalEnergyCharged")
            )

        return retval
