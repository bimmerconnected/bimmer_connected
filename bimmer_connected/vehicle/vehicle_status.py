"""Models the state of a vehicle."""

import datetime
import logging
from typing import TYPE_CHECKING, Dict, List, Optional

from bimmer_connected.utils import SerializableBaseClass
from bimmer_connected.vehicle.models import GPSPosition, ValueWithUnit

if TYPE_CHECKING:
    from bimmer_connected.vehicle import ConnectedDriveVehicle
    from bimmer_connected.vehicle.doors_windows import Lid, LockState, Window
    from bimmer_connected.vehicle.fuel_and_battery import ChargingState
    from bimmer_connected.vehicle.reports import CheckControlMessage, ConditionBasedService

_LOGGER = logging.getLogger(__name__)


def backend_parameter(func):
    """Decorator for parameters reading data from the backend.

    Errors are handled in a default way.
    """

    def _func_wrapper(self: "VehicleStatus", *args, **kwargs):
        # pylint: disable=protected-access
        try:
            return func(self, *args, **kwargs)
        except KeyError:
            _LOGGER.debug("No data available for attribute %s!", str(func))
            return None

    return _func_wrapper


class VehicleStatus(SerializableBaseClass):  # pylint: disable=too-many-public-methods
    """Models the status of a vehicle."""

    # pylint: disable=unused-argument
    def __init__(self, vehicle: "ConnectedDriveVehicle", status_dict: Dict = None):
        """Constructor."""
        self.vehicle = vehicle

    @property
    def timestamp(self) -> Optional[datetime.datetime]:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.timestamp

    @property
    def gps_position(self) -> GPSPosition:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.vehicle_location.location

    @property
    def gps_heading(self) -> Optional[int]:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.vehicle_location.heading

    @property
    def is_vehicle_active(self) -> bool:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.is_vehicle_active

    @property
    def mileage(self) -> ValueWithUnit:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.mileage

    @property
    def remaining_range_fuel(self) -> Optional[ValueWithUnit]:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.fuel_and_battery.remaining_range_fuel

    @property
    def remaining_fuel(self) -> Optional[ValueWithUnit]:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.fuel_and_battery.remaining_fuel

    @property
    def fuel_indicator_count(self) -> Optional[int]:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.fuel_indicator_count

    @property
    def lids(self) -> List["Lid"]:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.doors_and_windows.lids

    @property
    def open_lids(self) -> List["Lid"]:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.doors_and_windows.open_lids

    @property
    def all_lids_closed(self) -> bool:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.doors_and_windows.all_lids_closed

    @property
    def windows(self) -> List["Window"]:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.doors_and_windows.windows

    @property
    def open_windows(self) -> List["Window"]:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.doors_and_windows.open_windows

    @property
    def all_windows_closed(self) -> bool:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.doors_and_windows.all_lids_closed

    @property
    def door_lock_state(self) -> "LockState":
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.doors_and_windows.door_lock_state

    @property
    def last_update_reason(self) -> str:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.last_update_reason

    @property
    def last_charging_end_result(self) -> None:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return None  # Not available in My BMW

    @property
    def connection_status(self) -> str:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return "CONNECTED" if self.vehicle.fuel_and_battery.is_charger_connected else "DISCONNECTED"

    @property
    def condition_based_services(self) -> List["ConditionBasedService"]:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.condition_based_services.messages

    @property
    def are_all_cbs_ok(self) -> bool:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return not self.vehicle.condition_based_services.is_service_required

    @property
    def parking_lights(self) -> None:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return None  # Not available in My BMW

    @property
    def has_parking_light_state(self) -> bool:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return False  # Not available in My BMW

    @property
    def are_parking_lights_on(self) -> None:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return None  # Not available in My BMW

    @property
    def remaining_range_electric(self) -> Optional[ValueWithUnit]:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.fuel_and_battery.remaining_range_electric

    @property
    def remaining_range_total(self) -> Optional[ValueWithUnit]:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.fuel_and_battery.remaining_range_combined

    @property
    def max_range_electric(self) -> Optional[int]:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return None  # Not available in My BMW

    @property
    def charging_status(self) -> Optional["ChargingState"]:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.fuel_and_battery.charging_status

    @property
    def charging_time_remaining(self) -> None:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return None

    @property
    def charging_start_time(self) -> Optional[datetime.datetime]:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.fuel_and_battery.charging_start_time

    @property
    def charging_end_time(self) -> Optional[datetime.datetime]:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.fuel_and_battery.charging_end_time

    @property
    def charging_time_label(self) -> Optional[str]:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.fuel_and_battery.charging_time_label

    @property
    def charging_level_hv(self) -> Optional[int]:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.fuel_and_battery.remaining_battery_percent

    @property
    def fuel_percent(self) -> Optional[int]:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.fuel_and_battery.remaining_fuel_percent

    @property
    def check_control_messages(self) -> List["CheckControlMessage"]:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.check_control_messages.messages

    @property
    def has_check_control_messages(self) -> bool:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.check_control_messages.has_check_control_messages
