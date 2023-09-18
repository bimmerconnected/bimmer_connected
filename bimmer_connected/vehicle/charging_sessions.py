"""Models the charging sessions."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from bimmer_connected.const import ATTR_STATE
from bimmer_connected.models import VehicleDataBase, StrEnum


class ChargingType(StrEnum):
    """Possible charging types."""

    AC = "AC"
    AC_HIGH = "AC_HIGH"
    DC = "DC"
    UNKNOWN = "UNKNOWN"
    NA = "N/A"

    @classmethod
    def _missing_(cls, value):
        return cls.UNKNOWN


@dataclass
class ChargingSessions(VehicleDataBase):
    """Provides an accessible version of `charging_sessions`."""

    charging_session_count: int = None
    """Total number of charging sessions."""

    charging_sessions: list = field(default_factory=lambda: [])
    """List of charging sessions."""

    @classmethod
    def _parse_vehicle_data(cls, vehicle_data: Dict) -> Dict:
        """Parse charging statistics."""
        retval: Dict[str, Any] = {}

        if ATTR_STATE in vehicle_data:
            retval["charging_session_count"] = vehicle_data.get("chargingSessions", {}).get("numberOfSessions")

            charging_sessions = vehicle_data.get("chargingSessions", {}).get("sessions", [])

            _charging_sessions = []
            for charging_session in charging_sessions:
                _charging_sessions.append(
                    {
                        "status": charging_session.get("sessionStatus"),
                        "description": charging_session.get("title") + " \u2022 " + charging_session.get("subtitle"),
                        "address": charging_session.get("details", {}).get("address", "N/A").strip().title(),
                        "charging_type": ChargingType(charging_session.get("details", {}).get("chargingType", "N/A")),
                        "soc_start": charging_session.get("details", {}).get("startBatteryPc", "N/A"),
                        "soc_end": charging_session.get("details", {}).get("endBatteryPc", "N/A"),
                        "energy_charged": charging_session.get("details", {}).get("energyChargedValue", "N/A"),
                        "date_start": charging_session.get("details", {}).get("date", "N/A"),
                        "date_end": charging_session.get("details", {}).get("endDate", "N/A"),
                        "duration": charging_session.get("details", {}).get("duration", "N/A"),
                        "charging_speed_min": charging_session.get("details", {})
                        .get("chargingBlocks", {})
                        .get("min", "N/A"),
                        "charging_speed_max": charging_session.get("details", {})
                        .get("chargingBlocks", {})
                        .get("max", "N/A"),
                        "public": charging_session.get("isPublic"),
                        "pre_condition": charging_session.get("details", {}).get("preCondition", "N/A"),
                        "mileage": charging_session.get("details", {}).get("totalMileage", "N/A"),
                    }
                )

            retval["charging_sessions"] = _charging_sessions

        return retval
