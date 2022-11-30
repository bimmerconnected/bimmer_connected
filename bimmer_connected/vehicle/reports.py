"""Models the state of a vehicle."""

import datetime
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from bimmer_connected.const import ATTR_STATE
from bimmer_connected.models import StrEnum, ValueWithUnit, VehicleDataBase
from bimmer_connected.utils import parse_datetime

_LOGGER = logging.getLogger(__name__)


class ConditionBasedServiceStatus(StrEnum):
    """Status of the condition based services."""

    OK = "OK"
    OVERDUE = "OVERDUE"
    PENDING = "PENDING"
    UNKNOWN = "UNKNOWN"


@dataclass
class ConditionBasedService:  # pylint: disable=too-few-public-methods
    """Entry in the list of condition based services."""

    service_type: str
    state: ConditionBasedServiceStatus
    due_date: Optional[datetime.datetime]
    due_distance: ValueWithUnit

    # pylint:disable=invalid-name,redefined-builtin,too-many-arguments,unused-argument
    @classmethod
    def from_api_entry(
        cls,
        type: str,
        status: str,
        dateTime: Optional[str] = None,
        mileage: Optional[int] = None,
        is_metric: bool = True,
        **kwargs
    ):
        """Parse a condition based service entry from the API format to `ConditionBasedService`."""
        due_distance = ValueWithUnit(mileage, "km" if is_metric else "mi") if mileage else ValueWithUnit(None, None)
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

        if ATTR_STATE in vehicle_data and "requiredServices" in vehicle_data[ATTR_STATE]:
            messages = vehicle_data[ATTR_STATE]["requiredServices"]
            retval["messages"] = [
                ConditionBasedService.from_api_entry(**m, is_metric=vehicle_data["is_metric"]) for m in messages
            ]
            retval["is_service_required"] = any((m.state != ConditionBasedServiceStatus.OK) for m in retval["messages"])

        return retval


class CheckControlStatus(StrEnum):
    """Status of the condition based services."""

    OK = "OK"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


@dataclass
class CheckControlMessage:
    """Check control message sent from the server."""

    description_short: str
    description_long: Optional[str]
    state: CheckControlStatus

    # pylint:disable=invalid-name,redefined-builtin,unused-argument
    @classmethod
    def from_api_entry(cls, type: str, severity: str, longDescription: Optional[str] = None, **kwargs):
        """Parses a check control entry from the API format to `CheckControlMessage`."""
        return cls(type, longDescription, CheckControlStatus(severity))


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

        if ATTR_STATE in vehicle_data and "checkControlMessages" in vehicle_data[ATTR_STATE]:
            messages = vehicle_data[ATTR_STATE]["checkControlMessages"]
            retval["messages"] = [CheckControlMessage.from_api_entry(**m) for m in messages if m["severity"] != "OK"]
            retval["has_check_control_messages"] = len([m for m in retval["messages"] if m.state != "LOW"]) > 0

        return retval
