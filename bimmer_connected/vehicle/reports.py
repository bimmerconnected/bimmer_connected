"""Models the state of a vehicle."""

import datetime
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from bimmer_connected.utils import parse_datetime
from bimmer_connected.vehicle.models import StrEnum, ValueWithUnit, VehicleDataBase

_LOGGER = logging.getLogger(__name__)


class ConditionBasedServiceStatus(StrEnum):
    """Status of the condition based services."""

    OK = "OK"
    OVERDUE = "OVERDUE"
    PENDING = "PENDING"


@dataclass
class ConditionBasedService:  # pylint: disable=too-few-public-methods
    """Entry in the list of condition based services."""

    service_type: str
    state: ConditionBasedServiceStatus
    due_date: Optional[datetime.date]
    due_distance: ValueWithUnit

    # pylint:disable=invalid-name,unused-argument,redefined-builtin
    @classmethod
    def from_api_entry(cls, type: str, status: str, dateTime: str = None, distance: Dict = None, **kwargs):
        """Parse a condition based service entry from the API format to `ConditionBasedService`."""
        due_distance = ValueWithUnit(distance["value"], distance["units"]) if distance else ValueWithUnit(None, None)
        due_date = parse_datetime(dateTime) if dateTime else None
        return cls(type, ConditionBasedServiceStatus(status), due_date, due_distance)


@dataclass
class ConditionBasedServiceReport(VehicleDataBase):
    """Parses and summarizes condition based services (e.g. next oil service)."""

    messages: List[ConditionBasedService] = field(default_factory=list)
    """List of the condition based services."""

    is_service_required: bool = False
    """Indicates if a service is required."""

    @classmethod
    def _parse_vehicle_data(cls, vehicle_data: Dict) -> Optional[Dict]:
        """Parse doors and windows."""
        retval: Dict[str, Any] = {}

        if "properties" not in vehicle_data or "serviceRequired" not in vehicle_data["properties"]:
            _LOGGER.error("Unable to read data from `properties.serviceRequired`.")
            return retval

        messages = vehicle_data["properties"]["serviceRequired"]
        retval["messages"] = [ConditionBasedService.from_api_entry(**m) for m in messages]
        retval["is_service_required"] = vehicle_data["properties"]["isServiceRequired"]

        return retval


class CheckControlStatus(StrEnum):
    """Status of the condition based services."""

    OK = "OK"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class CheckControlMessage:
    """Check control message sent from the server."""

    description_short: str
    description_long: str
    state: CheckControlStatus

    # pylint:disable=invalid-name,unused-argument
    @classmethod
    def from_api_entry(cls, title: str, longDescription: str, state: str, **kwargs):
        """Parses a check control entry from the API format to `CheckControlMessage`."""
        return cls(title, longDescription, CheckControlStatus(state))


@dataclass
class CheckControlMessageReport(VehicleDataBase):
    """Parses and summarizes check control messages (e.g. low tire pressure)."""

    messages: List[CheckControlMessage] = field(default_factory=list)
    """List of check control messages."""

    has_check_control_messages: bool = False
    """Indicates if check control messages are present."""

    @classmethod
    def _parse_vehicle_data(cls, vehicle_data: Dict) -> Optional[Dict]:
        """Parse doors and windows."""
        retval: Dict[str, Any] = {}

        if "status" not in vehicle_data or "checkControlMessages" not in vehicle_data["status"]:
            _LOGGER.error("Unable to read data from `status.checkControlMessages`.")
            return retval

        messages = vehicle_data["status"]["checkControlMessages"]
        retval["messages"] = [CheckControlMessage.from_api_entry(**m) for m in messages if m["state"] != "OK"]
        retval["has_check_control_messages"] = vehicle_data["status"]["checkControlMessagesGeneralState"] != "No Issues"

        return retval
