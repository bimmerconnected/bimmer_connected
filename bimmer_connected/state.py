"""Models the state of a vehicle."""

import datetime
import logging
from enum import Enum
from typing import List

from bimmer_connected.const import VEHICLE_STATE_URL

_LOGGER = logging.getLogger(__name__)


LIDS = ['door_driver_front', 'door_passenger_front', 'door_driver_rear', 'door_passenger_rear',
        'hood_state', 'trunk_state']
WINDOWS = ['window_driver_front', 'window_passenger_front', 'window_driver_rear', 'window_passenger_rear',
           'sunroof_state']


class LidState(Enum):
    """Possible states of the hatch, trunk, doors, windows, sun roof."""
    CLOSED = 'CLOSED'
    OPEN = 'OPEN'
    INTERMEDIATE = 'INTERMEDIATE'


class LockState(Enum):
    """Possible states of the door locks."""
    LOCKED = 'LOCKED'
    SECURED = 'SECURED'
    SELECTIVELOCKED = 'SELECTIVELOCKED'
    UNLOCKED = 'UNLOCKED'


def backend_parameter(func):
    """Decorator for parameters reading data from the backend.

    Errors are handled in a default way.
    """
    def _func_wrapper(self: 'VehicleState', *args, **kwargs):
        # pylint: disable=protected-access
        if self._attributes is None:
            raise ValueError('No data available!')
        try:
            return func(self, *args, **kwargs)
        except KeyError:
            _LOGGER.error('No data available!')
            return None
    return _func_wrapper


class VehicleState(object):
    """Models the state of a vehicle."""

    def __init__(self, account, vehicle):
        """Constructor."""
        self._account = account
        self._vehicle = vehicle
        self._attributes = None

    def update_data(self) -> None:
        """Read new status data from the server."""
        _LOGGER.debug('requesting new data from connected drive')

        response = self._account.send_request(
            VEHICLE_STATE_URL.format(server=self._account.server_url, vin=self._vehicle.vin))

        attributes = response.json()['attributesMap']
        if attributes['head_unit'] not in ('NBTEvo', 'EntryEvo', 'NBT', 'EntryNav'):
            # NBTEvo = M2, EntryEvo = X1, NBT = i3, EntryNav = 225xe hybrid
            _LOGGER.warning('This library is not yet tested with this type of head unit: %s. If you experience any'
                            'problems open an issue at: '
                            'https://github.com/ChristianKuehnel/bimmer_connected/issues '
                            'And provide the logged attributes below.',
                            attributes['head_unit'])
            _LOGGER.warning(attributes)
        self._attributes = attributes
        _LOGGER.debug('received new data from connected drive')

    @property
    @backend_parameter
    def attributes(self) -> datetime.datetime:
        """Retrieve all attributes from the sever.

        This does not parse the results in any way.
        """
        return self._attributes

    @property
    @backend_parameter
    def timestamp(self) -> datetime.datetime:
        """Get the timestamp when the data was recorded."""
        unix_time = int(self._attributes['updateTime_converted_timestamp'])
        return datetime.datetime.fromtimestamp(unix_time/1000)

    @property
    @backend_parameter
    def gps_position(self) -> (float, float):
        """Get the last known position of the vehicle.

        Returns a tuple of (latitue, longitude).
        This only provides data, if the vehicle tracking is enabled!
        """
        if self.is_vehicle_tracking_enabled:
            return float(self._attributes['gps_lat']), float(self._attributes['gps_lng'])
        return None

    @property
    @backend_parameter
    def is_vehicle_tracking_enabled(self) -> bool:
        """Check if the position tracking of the vehicle is enabled"""
        return self._attributes['vehicle_tracking'] == '1'

    @property
    @backend_parameter
    def unit_of_length(self) -> str:
        """Get the unit in which the length is measured."""
        return self._attributes['unitOfLength']

    @property
    @backend_parameter
    def unit_of_volume(self) -> str:
        """Get the unit in which the volume of fuel is measured."""
        consumption = self._attributes['unitOfCombustionConsumption']
        return consumption.split('/')[0]

    @property
    @backend_parameter
    def mileage(self) -> float:
        """Get the mileage of the vehicle.

        Returns a tuple of (value, unit_of_measurement)
        """
        return float(self._attributes['mileage'])

    @property
    @backend_parameter
    def remaining_range_fuel(self) -> float:
        """Get the remaining range of the vehicle on fuel.

        Returns a tuple of (value, unit_of_measurement)
        """
        return float(self._attributes['beRemainingRangeFuel'])

    @property
    @backend_parameter
    def remaining_fuel(self) -> float:
        """Get the remaining fuel of the vehicle.

        Returns a tuple of (value, unit_of_measurement)
        """
        return float(self._attributes['remaining_fuel'])

    @property
    @backend_parameter
    def lids(self) -> List['Lid']:
        """Get all lids (doors+hatch+trunk) of the car."""
        result = []
        for lid in LIDS:
            if lid in self._attributes:
                result.append(Lid(lid, self._attributes[lid]))
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
        for lid in WINDOWS:
            if lid in self._attributes:
                result.append(Window(lid, self._attributes[lid]))
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
        return LockState(self._attributes['door_lock_state'])


class Lid(object):  # pylint: disable=too-few-public-methods
    """A lid of the vehicle.

    Lids are: Doors + Trunk + Hatch
    """

    def __init__(self, name: str, state: str):
        self.name = name
        self.state = LidState(state)

    @property
    def is_closed(self) -> bool:
        """Check if the lid is closed."""
        return self.state == LidState.CLOSED

    def __str__(self) -> str:
        return '{}: {}'.format(self.name, self.state.value)


class Window(Lid):  # pylint: disable=too-few-public-methods
    """A window of the vehicle.

    A windows can be a normal window of the car or the sun roof.
    """
    pass
