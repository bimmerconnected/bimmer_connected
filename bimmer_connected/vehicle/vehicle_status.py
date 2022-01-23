"""Models the state of a vehicle."""

import datetime
import logging
from typing import Dict, List, Tuple, TYPE_CHECKING

from bimmer_connected.utils import SerializableBaseClass
from bimmer_connected.vehicle.const import ChargingState

if TYPE_CHECKING:
    from bimmer_connected.vehicle import ConnectedDriveVehicle
    from bimmer_connected.vehicle.doors_windows import Lid, Window, LockState
    from bimmer_connected.vehicle.reports import ConditionBasedService, CheckControlMessage

_LOGGER = logging.getLogger(__name__)


def backend_parameter(func):
    """Decorator for parameters reading data from the backend.

    Errors are handled in a default way.
    """
    def _func_wrapper(self: 'VehicleStatus', *args, **kwargs):
        # pylint: disable=protected-access
        try:
            return func(self, *args, **kwargs)
        except KeyError:
            _LOGGER.debug('No data available for attribute %s!', str(func))
            return None
    return _func_wrapper


class VehicleStatus(SerializableBaseClass):  # pylint: disable=too-many-public-methods
    """Models the status of a vehicle."""

    # pylint: disable=unused-argument
    def __init__(self, vehicle: "ConnectedDriveVehicle", status_dict: Dict = None):
        """Constructor."""
        self.vehicle = vehicle

    @property
    @backend_parameter
    def timestamp(self) -> datetime.datetime:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.timestamp

    @property
    def gps_position(self) -> Tuple[float, float]:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.gps_position

    @property
    def gps_heading(self) -> int:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.gps_heading

    @property
    @backend_parameter
    def is_vehicle_active(self) -> bool:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.is_vehicle_active

    @property
    @backend_parameter
    def mileage(self) -> Tuple[int, str]:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.mileage

    @property
    @backend_parameter
    def remaining_range_fuel(self) -> Tuple[int, str]:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.remaining_range_fuel

    @property
    @backend_parameter
    def remaining_fuel(self) -> Tuple[int, str]:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.remaining_fuel

    @property
    @backend_parameter
    def fuel_indicator_count(self) -> int:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.fuel_indicator_count

    @property
    @backend_parameter
    def lids(self) -> List['Lid']:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.lids

    @property
    def open_lids(self) -> List['Lid']:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.open_lids

    @property
    def all_lids_closed(self) -> bool:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.all_lids_closed

    @property
    @backend_parameter
    def windows(self) -> List['Window']:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.windows

    @property
    def open_windows(self) -> List['Window']:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.open_windows

    @property
    def all_windows_closed(self) -> bool:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.all_lids_closed

    @property
    @backend_parameter
    def door_lock_state(self) -> "LockState":
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.door_lock_state

    @property
    @backend_parameter
    def last_update_reason(self) -> str:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.last_update_reason

    @property
    @backend_parameter
    def last_charging_end_result(self) -> str:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return None  # Not available in My BMW

    @property
    @backend_parameter
    def connection_status(self) -> str:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.connection_status

    @property
    @backend_parameter
    def condition_based_services(self) -> List['ConditionBasedService']:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.condition_based_services

    @property
    def are_all_cbs_ok(self) -> bool:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.are_all_cbs_ok

    @property
    @backend_parameter
    def parking_lights(self) -> None:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return None  # Not available in My BMW

    @property
    def has_parking_light_state(self) -> bool:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return False  # Not available in My BMW

    @property
    def are_parking_lights_on(self) -> bool:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return None  # Not available in My BMW

    @property
    @backend_parameter
    def remaining_range_electric(self) -> Tuple[int, str]:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.remaining_range_electric

    @property
    @backend_parameter
    def remaining_range_total(self) -> Tuple[int, str]:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.remaining_range_total

    @property
    @backend_parameter
    def max_range_electric(self) -> int:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return None  # Not available in My BMW

    @property
    @backend_parameter
    def charging_status(self) -> ChargingState:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.charging_status

    @property
    @backend_parameter
    def charging_time_remaining(self) -> float:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return None

    @property
    @backend_parameter
    def charging_start_time(self) -> datetime.datetime:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.charging_time_start

    @property
    @backend_parameter
    def charging_end_time(self) -> datetime.datetime:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.charging_time_end

    @property
    @backend_parameter
    def charging_time_label(self) -> datetime.datetime:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.charging_time_label

    @property
    @backend_parameter
    def charging_level_hv(self) -> int:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.remaining_battery_percent

    @property
    @backend_parameter
    def fuel_percent(self) -> int:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.remaining_fuel_percent

    @property
    @backend_parameter
    def check_control_messages(self) -> List["CheckControlMessage"]:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.check_control_messages

    @property
    @backend_parameter
    def has_check_control_messages(self) -> bool:
        # TODO: deprecation  pylint:disable=missing-function-docstring
        return self.vehicle.has_check_control_messages
