"""Models the charging sessions."""

import datetime
from dataclasses import dataclass
from typing import Any, Dict, Optional

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
        retval["power_avg"] = round(charging_block__data.get("averagePowerGridKw", -1.0), 2)

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

    soc_start: str
    """SOC at the beginning of the charge event."""

    soc_end: str
    """SOC at the end of the charge event."""

    energy_charged: float
    """Total energy in kWh charged."""

    time_start: Optional[datetime.datetime]
    """Time at the beginning of the charge event."""

    time_end: Optional[datetime.datetime]
    """Time at the end of the charge event."""

    duration: str
    """Duration of the charge event."""

    power_avg: float
    """Average charging speed."""

    power_min: float
    """Minimum charging speed."""

    power_max: float
    """Maximum charging speed."""

    charging_blocks: [ChargingBlock]
    """List of charging blocks."""

    public: bool
    """Was a public charger used."""

    pre_condition: str
    """Was the battery of the vehicle preconditioned for charging."""

    mileage: str
    """Mileage of vehicle at time of charge im km."""

    @classmethod
    def _parse_vehicle_data(cls, session_data: Dict) -> Dict:
        """Parse charging session."""
        retval: Dict[str, Any] = {}

        retval["status"] = session_data.get("sessionStatus")
        retval["description"] = session_data.get("title") + " \u2022 " + session_data.get("subtitle")
        retval["address"] = session_data.get("details", {}).get("address", "N/A").strip().title()
        retval["charging_type"] = ChargingType(session_data.get("details", {}).get("chargingType", "N/A"))
        retval["soc_start"] = session_data.get("details", {}).get("startBatteryPc", "N/A")
        retval["soc_end"] = session_data.get("details", {}).get("endBatteryPc", "N/A")
        retval["energy_charged"] = session_data.get("details", {}).get("energyChargedValue", "N/A")
        retval["time_start"] = session_data.get("details", {}).get("date", "N/A")
        retval["time_end"] = session_data.get("details", {}).get("endDate", "N/A")
        retval["duration"] = session_data.get("details", {}).get("duration", "N/A")
        retval["power_avg"] = round(session_data.get("details", {}).get("chargingBlocks", {}).get("average", -1.0), 2)
        retval["power_min"] = round(session_data.get("details", {}).get("chargingBlocks", {}).get("min", -1.0), 2)
        retval["power_max"] = round(session_data.get("details", {}).get("chargingBlocks", {}).get("max", -1.0), 2)
        retval["public"] = session_data.get("isPublic")
        retval["pre_condition"] = session_data.get("details", {}).get("preCondition", "N/A")
        retval["mileage"] = session_data.get("details", {}).get("totalMileage", "N/A")

        charging_blocks = session_data.get("details", {}).get("chargingBlocks", {}).get("chargingBlockList", [])
        _charging_blocks = []
        for charging_block in charging_blocks:
            _charging_blocks.append(ChargingBlock.from_vehicle_data(charging_block))

        retval["charging_blocks"] = _charging_blocks

        return retval


@dataclass
class ChargingSessions(VehicleDataBase):
    """Provides an accessible version of `charging_sessions`."""

    charging_session_count: int
    """Total number of charging sessions."""

    charging_sessions: [ChargingSession]
    """List of charging sessions."""

    @classmethod
    def _parse_vehicle_data(cls, vehicle_data: Dict) -> Dict:
        """Parse charging statistics."""
        retval: Dict[str, Any] = {}

        if ATTR_CHARGING_SESSIONS in vehicle_data:
            retval["charging_session_count"] = int(vehicle_data.get("chargingSessions", {}).get("numberOfSessions", 0))

            charging_sessions_data = vehicle_data.get("chargingSessions", {}).get("sessions", [])

            _charging_sessions = []
            for charging_session in charging_sessions_data:
                _charging_sessions.append(ChargingSession.from_vehicle_data(charging_session))

            retval["charging_sessions"] = _charging_sessions

        return retval
