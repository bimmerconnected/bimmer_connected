"""Models the state of a vehicle."""

import datetime
import logging
from enum import Enum
from typing import List

from bimmer_connected.const import SERVICE_STATUS

_LOGGER = logging.getLogger(__name__)


LIDS = ['doorDriverFront', 'doorPassengerFront', 'doorDriverRear', 'doorPassengerRear',
        'hood', 'trunk']

WINDOWS = ['windowDriverFront', 'windowPassengerFront', 'windowDriverRear', 'windowPassengerRear', 'rearWindow',
           'sunroof']


class LidState(Enum):
    """Possible states of the hatch, trunk, doors, windows, sun roof."""
    CLOSED = 'CLOSED'
    OPEN = 'OPEN'
    OPEN_TILT = 'OPEN_TILT'
    INTERMEDIATE = 'INTERMEDIATE'
    INVALID = 'INVALID'


class LockState(Enum):
    """Possible states of the door locks."""
    LOCKED = 'LOCKED'
    SECURED = 'SECURED'
    SELECTIVE_LOCKED = 'SELECTIVE_LOCKED'
    UNLOCKED = 'UNLOCKED'


class ParkingLightState(Enum):
    """Possible states of the parking lights"""
    LEFT = 'LEFT'
    RIGHT = 'RIGHT'
    OFF = 'OFF'


class ConditionBasedServiceStatus(Enum):
    """Status of the condition based services."""
    OK = 'OK'
    OVERDUE = 'OVERDUE'
    PENDING = 'PENDING'


class ChargingState(Enum):
    """Charging state of electric vehicle."""
    CHARGING = 'CHARGING'
    ERROR = 'ERROR'
    FINISHED_FULLY_CHARGED = 'FINISHED_FULLY_CHARGED'
    FINISHED_NOT_FULL = 'FINISHED_NOT_FULL'
    INVALID = 'INVALID'
    NOT_CHARGING = 'NOT_CHARGING'
    WAITING_FOR_CHARGING = 'WAITING_FOR_CHARGING'


class CheckControlMessage:
    """Check control message sent from the server.

    This class provides a nicer API than parsing the JSON format directly.
    """

    def __init__(self, ccm_dict: dict):
        self._ccm_dict = ccm_dict

    @property
    def description_long(self) -> str:
        """Long description of the check control message."""
        return self._ccm_dict["ccmDescriptionLong"]

    @property
    def description_short(self) -> str:
        """Short description of the check control message."""
        return self._ccm_dict["ccmDescriptionShort"]

    @property
    def ccm_id(self) -> int:
        """id of the check control message."""
        return int(self._ccm_dict["ccmId"])

    @property
    def mileage(self) -> int:
        """Mileage of the vehicle when the check control message appeared."""
        return int(self._ccm_dict["ccmMileage"])


def backend_parameter(func):
    """Decorator for parameters reading data from the backend.

    Errors are handled in a default way.
    """
    def _func_wrapper(self: 'VehicleStatus', *args, **kwargs):
        # pylint: disable=protected-access
        if self._state.attributes[SERVICE_STATUS] is None:
            raise ValueError('No data available for vehicle status!')
        try:
            return func(self, *args, **kwargs)
        except KeyError:
            _LOGGER.debug('No data available for attribute %s!', str(func))
            return None
    return _func_wrapper


class VehicleStatus:  # pylint: disable=too-many-public-methods
    """Models the status of a vehicle."""

    def __init__(self, state):
        """Constructor."""
        self._state = state

    @property
    @backend_parameter
    def attributes(self) -> dict:
        """Retrieve all attributes from the sever.

        This does not parse the results in any way.
        """
        return self._state.attributes[SERVICE_STATUS]

    @property
    @backend_parameter
    def timestamp(self) -> datetime.datetime:
        """Get the timestamp when the data was recorded."""
        return self._parse_datetime(self._state.attributes[SERVICE_STATUS]['updateTime'])

    @property
    @backend_parameter
    def gps_position(self) -> (float, float):
        """Get the last known position of the vehicle.

        Returns a tuple of (latitude, longitude).
        This only provides data, if the vehicle tracking is enabled!
        """
        if not self.is_vehicle_tracking_enabled:
            _LOGGER.warning('Vehicle tracking is disabled')
            return None
        if self.is_vehicle_active:
            _LOGGER.warning('Vehicle was moving at last update, no position available')
            return None
        pos = self._state.attributes[SERVICE_STATUS]['position']
        return float(pos['lat']), float(pos['lon'])

    @property
    @backend_parameter
    def gps_heading(self) -> (int):
        """Get the last known heading of the vehicle.

        This only provides data, if the vehicle tracking is enabled!
        """
        if not self.is_vehicle_tracking_enabled:
            _LOGGER.warning('Vehicle tracking is disabled')
            return None
        if self.is_vehicle_active:
            _LOGGER.warning('Vehicle was moving at last update, no position available')
            return None
        pos = self._state.attributes[SERVICE_STATUS]['position']
        return int(pos['heading'])

    @property
    @backend_parameter
    def is_vehicle_active(self) -> bool:
        """Check if the vehicle is active/moving.

        If the vehicle was active/moving at the time of the last status update, current position is not available.
        """
        return self._state.attributes[SERVICE_STATUS]['position']['status'] in ['VEHICLE_ACTIVE']

    @property
    @backend_parameter
    def is_vehicle_tracking_enabled(self) -> bool:
        """Check if the position tracking of the vehicle is enabled.

        The server return "OK" if tracking is enabled and "DRIVER_DISABLED" if it is disabled in the vehicle.
        """
        return self._state.attributes[SERVICE_STATUS]['position']['status'] not in ['DRIVER_DISABLED', 'TOO_FAR_AWAY']

    @property
    @backend_parameter
    def mileage(self) -> int:
        """Get the mileage of the vehicle.

        Returns a tuple of (value, unit_of_measurement)
        """
        return int(self._state.attributes[SERVICE_STATUS]['mileage'])

    @property
    @backend_parameter
    def remaining_range_fuel(self) -> int:
        """Get the remaining range of the vehicle on fuel.

        Returns a tuple of (value, unit_of_measurement)
        """
        return int(self._state.attributes[SERVICE_STATUS]['remainingRangeFuel'])

    @property
    @backend_parameter
    def remaining_fuel(self) -> int:
        """Get the remaining fuel of the vehicle.

        Returns a tuple of (value, unit_of_measurement)
        """
        return int(self._state.attributes[SERVICE_STATUS]['remainingFuel'])

    @property
    @backend_parameter
    def lids(self) -> List['Lid']:
        """Get all lids (doors+hatch+trunk) of the car."""
        result = []
        for lid in LIDS:
            if lid in self._state.attributes[SERVICE_STATUS] and \
                    self._state.attributes[SERVICE_STATUS][lid] != LidState.INVALID.value:
                result.append(Lid(self, lid))
        return result

    @property
    def open_lids(self) -> List['Lid']:
        """Get all open lids of the car."""
        return [lid for lid in self.lids if not lid.is_closed]

    @property
    def all_lids_closed(self) -> bool:
        """Check if all lids are closed."""
        return len(list(self.open_lids)) == 0

    @property
    @backend_parameter
    def windows(self) -> List['Window']:
        """Get all windows (doors+sun roof) of the car."""
        result = []
        for window in WINDOWS:
            if window in self._state.attributes[SERVICE_STATUS] and \
                    self._state.attributes[SERVICE_STATUS][window] != LidState.INVALID.value:
                result.append(Window(self, window))
        return result

    @property
    def open_windows(self) -> List['Window']:
        """Get all open windows of the car."""
        return [lid for lid in self.windows if not lid.is_closed]

    @property
    def all_windows_closed(self) -> bool:
        """Check if all windows are closed."""
        return len(list(self.open_windows)) == 0

    @property
    @backend_parameter
    def door_lock_state(self) -> LockState:
        """Get state of the door locks."""
        return LockState(self._state.attributes[SERVICE_STATUS]['doorLockState'])

    @property
    @backend_parameter
    def last_update_reason(self) -> str:
        """The reason for the last state update"""
        return self._state.attributes[SERVICE_STATUS]['updateReason']

    @property
    @backend_parameter
    def last_charging_end_result(self) -> str:
        """Get the last charging end result"""
        return self._state.attributes[SERVICE_STATUS]['lastChargingEndResult']

    @property
    @backend_parameter
    def connection_status(self) -> str:
        """Get status of the connection"""
        return self._state.attributes[SERVICE_STATUS]['connectionStatus']

    @property
    @backend_parameter
    def condition_based_services(self) -> List['ConditionBasedServiceReport']:
        """Get status of the condition based services."""
        return [ConditionBasedServiceReport(s) for s in self._state.attributes[SERVICE_STATUS]['cbsData']]

    @property
    def are_all_cbs_ok(self) -> bool:
        """Check if the status of all condition based services is "OK"."""
        for cbs in self.condition_based_services:
            if cbs.state != ConditionBasedServiceStatus.OK:
                return False
        return True

    @property
    @backend_parameter
    def parking_lights(self) -> ParkingLightState:
        """Get status of parking lights.

        :returns None if status is unknown.
        """
        return ParkingLightState(self._state.attributes[SERVICE_STATUS]['parkingLight'])

    @property
    def has_parking_light_state(self) -> bool:
        """Return True if parking light is available."""
        return 'parkingLight' in self._state.attributes[SERVICE_STATUS]

    @property
    def are_parking_lights_on(self) -> bool:
        """Get status of parking lights.

        :returns None if status is unknown.
        """
        lights = self.parking_lights
        if lights is None:
            return None
        return lights != ParkingLightState.OFF

    @staticmethod
    def _parse_datetime(date_str: str) -> datetime.datetime:
        """Convert a time string into datetime."""
        date_format = "%Y-%m-%dT%H:%M:%S%z"
        return datetime.datetime.strptime(date_str, date_format)

    def __getattr__(self, item):
        """Generic get function for all backend attributes."""
        return self._state.attributes[SERVICE_STATUS][item]

    @property
    @backend_parameter
    def remaining_range_electric(self) -> int:
        """Remaining range on battery, in kilometers."""
        return int(self._state.attributes[SERVICE_STATUS]['remainingRangeElectric'])

    @property
    @backend_parameter
    def remaining_range_total(self) -> int:
        """Get the total remaining range of the vehicle in kilometers.

        That is electrical range + fuel range.
        """
        result = 0
        if self.remaining_range_electric is not None:
            result += self.remaining_range_electric
        if self.remaining_range_fuel is not None:
            result += self.remaining_range_fuel
        return result

    @property
    @backend_parameter
    def max_range_electric(self) -> int:
        """ This can change with driving style and temperature in kilometers."""
        return int(self._state.attributes[SERVICE_STATUS]['maxRangeElectric'])

    @property
    @backend_parameter
    def charging_status(self) -> ChargingState:
        """Charging state of the vehicle."""
        state = self._state.attributes[SERVICE_STATUS]['chargingStatus']
        return ChargingState(state)

    @property
    @backend_parameter
    def charging_time_remaining(self) -> datetime.timedelta:
        """Get the remaining charging time."""
        minutes = self._state.attributes[SERVICE_STATUS]['chargingTimeRemaining']
        return datetime.timedelta(minutes=minutes)

    @property
    @backend_parameter
    def charging_level_hv(self) -> int:
        """State of charge of the high voltage battery in percent."""
        return int(self._state.attributes[SERVICE_STATUS]['chargingLevelHv'])

    @property
    @backend_parameter
    def fuel_percent(self) -> int:
        """State of fuel in percent."""
        return int(self._state.attributes[SERVICE_STATUS]['fuelPercent'])

    @property
    @backend_parameter
    def check_control_messages(self) -> List[CheckControlMessage]:
        """List of check control messages."""
        # TO DO change this in HA binary_sensor.py first
        # messages = self._state.attributes[SERVICE_STATUS]['STATUS'].get('checkControlMessages', [])
        # return [CheckControlMessage(m) for m in messages]
        return self._state.attributes[SERVICE_STATUS].get('checkControlMessages', [])

    @property
    @backend_parameter
    def has_check_control_messages(self) -> bool:
        """Return true if any check control message is present."""
        return len(self.check_control_messages) > 0


class Lid:  # pylint: disable=too-few-public-methods
    """A lid of the vehicle.

    Lids are: Doors + Trunk + Hatch
    """

    def __init__(self, vehicle_status: VehicleStatus, name: str):
        #: name of the lid
        self.name = name
        self._vehicle_status = vehicle_status

    @property
    def state(self):
        """Get the current state of the lid."""
        return LidState(getattr(self._vehicle_status, self.name))

    @property
    def is_closed(self) -> bool:
        """Check if the lid is closed."""
        return self.state == LidState.CLOSED

    def __str__(self) -> str:
        return '{}: {}'.format(self.name, self._vehicle_status)


class Window(Lid):  # pylint: disable=too-few-public-methods
    """A window of the vehicle.

    A window can be a normal window of the car or the sun roof.
    """


class ConditionBasedServiceReport:  # pylint: disable=too-few-public-methods
    """Entry in the list of condition based services."""

    def __init__(self, data: dict):

        #: date when the service is due
        self.due_date = self._parse_date(data.get('cbsDueDate'))

        #: status of the service
        self.state = ConditionBasedServiceStatus(data['cbsState'])

        #: service type
        self.service_type = data['cbsType']

        #: distance when the service is due
        self.due_distance = None
        if 'cbsRemainingMileage' in data:
            self.due_distance = int(data['cbsRemainingMileage'])

        #: description of the required service
        self.description = data['cbsDescription']

    @staticmethod
    def _parse_date(datestr: str) -> datetime.datetime:
        if datestr is None:
            return None
        formats = [
            '%Y-%m',
            '%m.%Y',
        ]
        for date_format in formats:
            try:
                date = datetime.datetime.strptime(datestr, date_format)
                return date.replace(day=1)
            except ValueError:
                pass
        _LOGGER.error('Unknown time format for CBS: %s', datestr)
        return None
