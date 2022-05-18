"""Models the state of a vehicle."""

import datetime
import logging
from typing import TYPE_CHECKING, Dict, List, Optional

from bimmer_connected.utils import deprecated
from bimmer_connected.vehicle.models import GPSPosition, ValueWithUnit

if TYPE_CHECKING:
    from bimmer_connected.vehicle import MyBMWVehicle
    from bimmer_connected.vehicle.doors_windows import Lid, LockState, Window
    from bimmer_connected.vehicle.fuel_and_battery import ChargingState
    from bimmer_connected.vehicle.reports import CheckControlMessage, ConditionBasedService

_LOGGER = logging.getLogger(__name__)


class VehicleStatus:  # pylint: disable=too-many-public-methods
    """Models the status of a vehicle."""

    # pylint: disable=unused-argument
    def __init__(self, vehicle: "MyBMWVehicle", status_dict: Dict = None):
        """Constructor."""
        self.vehicle = vehicle

    @property  # type: ignore[misc]
    @deprecated("vehicle.timestamp")
    def timestamp(self) -> Optional[datetime.datetime]:
        # pylint:disable=missing-function-docstring
        return self.vehicle.timestamp

    @property  # type: ignore[misc]
    @deprecated("vehicle.vehicle_location.location")
    def gps_position(self) -> GPSPosition:
        # pylint:disable=missing-function-docstring
        return self.vehicle.vehicle_location.location

    @property  # type: ignore[misc]
    @deprecated("vehicle.vehicle_location.heading")
    def gps_heading(self) -> Optional[int]:
        # pylint:disable=missing-function-docstring
        return self.vehicle.vehicle_location.heading

    @property  # type: ignore[misc]
    @deprecated("vehicle.is_vehicle_active")
    def is_vehicle_active(self) -> bool:
        # pylint:disable=missing-function-docstring
        return self.vehicle.is_vehicle_active

    @property  # type: ignore[misc]
    @deprecated("vehicle.mileage")
    def mileage(self) -> ValueWithUnit:
        # pylint:disable=missing-function-docstring
        return self.vehicle.mileage

    @property  # type: ignore[misc]
    @deprecated("vehicle.fuel_and_battery.remaining_range_fuel")
    def remaining_range_fuel(self) -> Optional[ValueWithUnit]:
        # pylint:disable=missing-function-docstring
        return self.vehicle.fuel_and_battery.remaining_range_fuel

    @property  # type: ignore[misc]
    @deprecated("vehicle.fuel_and_battery.remaining_fuel")
    def remaining_fuel(self) -> Optional[ValueWithUnit]:
        # pylint:disable=missing-function-docstring
        return self.vehicle.fuel_and_battery.remaining_fuel

    @property  # type: ignore[misc]
    @deprecated("vehicle.fuel_indicator_count")
    def fuel_indicator_count(self) -> Optional[int]:
        # pylint:disable=missing-function-docstring
        return self.vehicle.fuel_indicator_count

    @property  # type: ignore[misc]
    @deprecated("vehicle.doors_and_windows.lids")
    def lids(self) -> List["Lid"]:
        # pylint:disable=missing-function-docstring
        return self.vehicle.doors_and_windows.lids

    @property  # type: ignore[misc]
    @deprecated("vehicle.doors_and_windows.open_lids")
    def open_lids(self) -> List["Lid"]:
        # pylint:disable=missing-function-docstring
        return self.vehicle.doors_and_windows.open_lids

    @property  # type: ignore[misc]
    @deprecated("vehicle.doors_and_windows.all_lids_closed")
    def all_lids_closed(self) -> bool:
        # pylint:disable=missing-function-docstring
        return self.vehicle.doors_and_windows.all_lids_closed

    @property  # type: ignore[misc]
    @deprecated("vehicle.doors_and_windows.windows")
    def windows(self) -> List["Window"]:
        # pylint:disable=missing-function-docstring
        return self.vehicle.doors_and_windows.windows

    @property  # type: ignore[misc]
    @deprecated("vehicle.doors_and_windows.open_windows")
    def open_windows(self) -> List["Window"]:
        # pylint:disable=missing-function-docstring
        return self.vehicle.doors_and_windows.open_windows

    @property  # type: ignore[misc]
    @deprecated("vehicle.doors_and_windows.all_lids_closed")
    def all_windows_closed(self) -> bool:
        # pylint:disable=missing-function-docstring
        return self.vehicle.doors_and_windows.all_lids_closed

    @property  # type: ignore[misc]
    @deprecated("vehicle.doors_and_windows.door_lock_state")
    def door_lock_state(self) -> "LockState":
        # pylint:disable=missing-function-docstring
        return self.vehicle.doors_and_windows.door_lock_state

    @property  # type: ignore[misc]
    @deprecated("vehicle.last_update_reason")
    def last_update_reason(self) -> str:
        # pylint:disable=missing-function-docstring
        return self.vehicle.last_update_reason

    @property  # type: ignore[misc]
    @deprecated()
    def last_charging_end_result(self) -> None:
        # pylint:disable=missing-function-docstring
        return None  # Not available in My BMW

    @property  # type: ignore[misc]
    @deprecated("vehicle.fuel_and_battery.is_charger_connected")
    def connection_status(self) -> str:
        # pylint:disable=missing-function-docstring
        return "CONNECTED" if self.vehicle.fuel_and_battery.is_charger_connected else "DISCONNECTED"

    @property  # type: ignore[misc]
    @deprecated("vehicle.condition_based_services.messages")
    def condition_based_services(self) -> List["ConditionBasedService"]:
        # pylint:disable=missing-function-docstring
        return self.vehicle.condition_based_services.messages

    @property  # type: ignore[misc]
    @deprecated("vehicle.condition_based_services.is_service_required")
    def are_all_cbs_ok(self) -> bool:
        # pylint:disable=missing-function-docstring
        return not self.vehicle.condition_based_services.is_service_required

    @property  # type: ignore[misc]
    @deprecated()
    def parking_lights(self) -> None:
        # pylint:disable=missing-function-docstring
        return None  # Not available in My BMW

    @property  # type: ignore[misc]
    @deprecated()
    def has_parking_light_state(self) -> bool:
        # pylint:disable=missing-function-docstring
        return False  # Not available in My BMW

    @property  # type: ignore[misc]
    @deprecated()
    def are_parking_lights_on(self) -> None:
        # pylint:disable=missing-function-docstring
        return None  # Not available in My BMW

    @property  # type: ignore[misc]
    @deprecated("vehicle.fuel_and_battery.remaining_range_electric")
    def remaining_range_electric(self) -> Optional[ValueWithUnit]:
        # pylint:disable=missing-function-docstring
        return self.vehicle.fuel_and_battery.remaining_range_electric

    @property  # type: ignore[misc]
    @deprecated("vehicle.fuel_and_battery.remaining_range_total")
    def remaining_range_total(self) -> Optional[ValueWithUnit]:
        # pylint:disable=missing-function-docstring
        return self.vehicle.fuel_and_battery.remaining_range_total

    @property  # type: ignore[misc]
    @deprecated()
    def max_range_electric(self) -> Optional[int]:
        # pylint:disable=missing-function-docstring
        return None  # Not available in My BMW

    @property  # type: ignore[misc]
    @deprecated("vehicle.fuel_and_battery.charging_status")
    def charging_status(self) -> Optional["ChargingState"]:
        # pylint:disable=missing-function-docstring
        return self.vehicle.fuel_and_battery.charging_status

    @property  # type: ignore[misc]
    @deprecated()
    def charging_time_remaining(self) -> None:
        # pylint:disable=missing-function-docstring
        return None

    @property  # type: ignore[misc]
    @deprecated("vehicle.fuel_and_battery.charging_start_time")
    def charging_start_time(self) -> Optional[datetime.datetime]:
        # pylint:disable=missing-function-docstring
        return self.vehicle.fuel_and_battery.charging_start_time

    @property  # type: ignore[misc]
    @deprecated("vehicle.fuel_and_battery.charging_end_time")
    def charging_end_time(self) -> Optional[datetime.datetime]:
        # pylint:disable=missing-function-docstring
        return self.vehicle.fuel_and_battery.charging_end_time

    @property  # type: ignore[misc]
    @deprecated("vehicle.fuel_and_battery.charging_time_label")
    def charging_time_label(self) -> Optional[str]:
        # pylint:disable=missing-function-docstring
        return self.vehicle.fuel_and_battery.charging_time_label

    @property  # type: ignore[misc]
    @deprecated("vehicle.fuel_and_battery.remaining_battery_percent")
    def charging_level_hv(self) -> Optional[int]:
        # pylint:disable=missing-function-docstring
        return self.vehicle.fuel_and_battery.remaining_battery_percent

    @property  # type: ignore[misc]
    @deprecated("vehicle.fuel_and_battery.remaining_fuel_percent")
    def fuel_percent(self) -> Optional[int]:
        # pylint:disable=missing-function-docstring
        return self.vehicle.fuel_and_battery.remaining_fuel_percent

    @property  # type: ignore[misc]
    @deprecated("vehicle.check_control_messages.messages")
    def check_control_messages(self) -> List["CheckControlMessage"]:
        # pylint:disable=missing-function-docstring
        return self.vehicle.check_control_messages.messages

    @property  # type: ignore[misc]
    @deprecated("vehicle.check_control_messages.has_check_control_messages")
    def has_check_control_messages(self) -> bool:
        # pylint:disable=missing-function-docstring
        return self.vehicle.check_control_messages.has_check_control_messages
