"""Models the charging sessions."""

import datetime
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from bimmer_connected.const import ATTR_CHARGING_SESSIONS
from bimmer_connected.models import StrEnum, VehicleDataBase


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
class ChargingBlock(VehicleDataBase):
    """Provides an accessible version of a single charging block."""

    time_start: Optional[datetime.datetime]
    """Address of charger used."""

    time_end: Optional[datetime.datetime]
    """Type of charger used."""

    power_avg: float
    """Summary of the charge event."""

    @classmethod
    def _parse_vehicle_data(cls, charging_block__data: Dict) -> Dict:
        """Parse charging session."""
        retval: Dict[str, Any] = {}

        retval["time_start"] = charging_block__data.get("startTime")
        retval["time_end"] = charging_block__data.get("endTime")
        retval["power_avg"] = round(charging_block__data.get("averagePowerGridKw", 0), 2)

        return retval


@dataclass
class ChargingSession(VehicleDataBase):
    """Provides an accessible version of a single charging session."""

    status: str
    """Final status of the charge event."""

    description: str
    """Summary of the charge event."""

    address: str
    """Address of charger used."""

    charging_type: ChargingType
    """Type of charger used."""

    soc_start: float
    """SOC at the beginning of the charge event."""

    soc_end: float
    """SOC at the end of the charge event."""

    energy_charged: float
    """Total energy in kWh charged."""

    time_start: datetime.datetime
    """Time at the beginning of the charge event."""

    time_end: datetime.datetime
    """Time at the end of the charge event."""

    duration: int
    """Duration of the charge event in minutes."""

    power_avg: float
    """Average charging speed."""

    power_min: float
    """Minimum charging speed."""

    power_max: float
    """Maximum charging speed."""

    charging_blocks: List[ChargingBlock]
    """List of charging blocks."""

    public: bool
    """Was a public charger used."""

    pre_condition: str
    """Was the battery of the vehicle preconditioned for charging."""

    mileage: int
    """Mileage of vehicle at time of charge im km."""

    @classmethod
    def _parse_vehicle_data(cls, session_data: Dict) -> Dict:
        """Parse charging session."""
        retval: Dict[str, Any] = {}

        retval["status"] = session_data.get("sessionStatus")
        retval["description"] = session_data.get("title", "") + " \u2022 " + session_data.get("subtitle", "")
        retval["address"] = session_data.get("details", {}).get("address", "N/A").strip().title()
        retval["charging_type"] = ChargingType(session_data.get("details", {}).get("chargingType", "N/A"))
        retval["soc_start"] = float(session_data.get("details", {}).get("startBatteryPc", "0%").strip("%")) / 100
        retval["soc_end"] = float(session_data.get("details", {}).get("endBatteryPc", "0%").strip("%")) / 100
        retval["energy_charged"] = round(session_data.get("details", {}).get("energyChargedValue", 0), 2)
        retval["time_start"] = datetime.datetime.strptime(
            session_data.get("details", {}).get("date", None), "%d/%m/%Y %H:%M"
        )
        retval["time_end"] = datetime.datetime.strptime(
            session_data.get("details", {}).get("endDate", None), "%d/%m/%Y %H:%M"
        )

        duration = session_data.get("details", {}).get("duration", "")
        match = re.match(r"^(?:(\d+)h )?(\d+) ?min$", duration)
        retval["duration"] = (
            int(
                datetime.timedelta(hours=int(match.group(1) or 0), minutes=int(match.group(2) or 0)).total_seconds()
                / 60
            )
            if match
            else -1
        )

        retval["public"] = session_data.get("isPublic")
        retval["pre_condition"] = True if session_data.get("details", {}).get("preCondition", "N/A") == "On" else False
        retval["mileage"] = int("".join(filter(str.isdigit, session_data.get("details", {}).get("totalMileage", "0"))))

        # Handle charging blocks
        charging_blocks = session_data.get("details", {}).get("chargingBlocks", {}).get("chargingBlockList", [])
        retval["charging_blocks"] = [ChargingBlock.from_vehicle_data(cb) for cb in charging_blocks]
        retval["power_avg"] = round(session_data.get("details", {}).get("chargingBlocks", {}).get("average", 0), 2)
        retval["power_min"] = round(session_data.get("details", {}).get("chargingBlocks", {}).get("min", 0), 2)
        retval["power_max"] = round(session_data.get("details", {}).get("chargingBlocks", {}).get("max", 0), 2)

        return retval


@dataclass
class ChargingSessions(VehicleDataBase):
    """Provides an accessible version of `charging_sessions`."""

    charging_session_count: int
    """Total number of charging sessions."""

    charging_sessions: List[ChargingSession]
    """List of charging sessions."""

    @classmethod
    def _parse_vehicle_data(cls, vehicle_data: Dict) -> Dict:
        """Parse charging statistics."""
        retval: Dict[str, Any] = {}

        if ATTR_CHARGING_SESSIONS in vehicle_data:
            retval["charging_session_count"] = int(vehicle_data.get("chargingSessions", {}).get("numberOfSessions", 0))
            charging_sessions_data = vehicle_data.get("chargingSessions", {}).get("sessions", [])
            retval["charging_sessions"] = [ChargingSession.from_vehicle_data(cs) for cs in charging_sessions_data]

        return retval
