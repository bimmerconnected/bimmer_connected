"""Models the state of a vehicle."""

import datetime
import logging

_LOGGER = logging.getLogger(__name__)

VEHICLE_STATE_URL = '{server}/api/vehicle/dynamic/v1/{vin}'


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
            raise ValueError('No data available!')
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

        Returns a tuple of (latitue, longitude)
        """
        if self._attributes['vehicle_tracking'] == '1':
            return float(self._attributes['gps_lat']), float(self._attributes['gps_lng'])
        return None

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
