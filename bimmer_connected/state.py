"""Models the state of a vehicle."""

import datetime
import logging
from threading import Lock
import requests

_LOGGER = logging.getLogger(__name__)

VEHICLE_STATE_URL = '{server}/api/vehicle/dynamic/v1/{vin}'


def backend_parameter(func):
    """Decorator for parameters reading data from the backend.

    Errors are handled in a default way and updating the caching is done as required.
    """
    def _func_wrapper(self: 'VehicleState', *args, **kwargs):
        # pylint: disable=protected-access
        self.update_cache()
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
        self._cache_expiration = datetime.datetime.now()
        self._update_lock = Lock()

    def _update_data(self) -> None:
        """Read new status data from the server."""
        _LOGGER.debug('requesting new data from connected drive')
        headers = self._account.request_header

        response = requests.get(VEHICLE_STATE_URL.format(server=self._account.server_url, vin=self._vehicle.vin),
                                headers=headers, allow_redirects=True)

        if response.status_code != 200:
            raise IOError('Unknown status code {}'.format(response.status_code))

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

    def update_cache(self):
        """Update the cache if required."""
        if self._attributes is None or self._account.cache and datetime.datetime.now() > self._cache_expiration:
            with self._update_lock:
                self._update_data()
                self._cache_expiration = datetime.datetime.now() + \
                    datetime.timedelta(seconds=self._account.cache_timeout)

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
