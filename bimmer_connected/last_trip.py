"""Models the last trip of a vehicle."""

import logging
from typing import List

from bimmer_connected.const import SERVICE_LAST_TRIP

_LOGGER = logging.getLogger(__name__)


def backend_parameter(func):
    """Decorator for parameters reading data from the backend.

    Errors are handled in a default way.
    """
    def _func_wrapper(self: 'LastTrip', *args, **kwargs):
        # pylint: disable=protected-access
        if self._state.attributes[SERVICE_LAST_TRIP] is None:
            raise ValueError('No data available for vehicle last trips!')
        try:
            return func(self, *args, **kwargs)
        except KeyError:
            _LOGGER.debug('No data available for attribute %s!', str(func))
            return None
    return _func_wrapper


class LastTrip:  # pylint: disable=too-many-public-methods
    """Models the last trip of a vehicle."""

    def __init__(self, state):
        """Constructor."""
        self._state = state

    @property
    @backend_parameter
    def attributes(self) -> dict:
        """Retrieve all attributes from the server.

        This does not parse the results in any way.
        """
        return self._state.attributes[SERVICE_LAST_TRIP]

    def __getattr__(self, item):
        """Generic get function for all backend attributes."""
        return self._state.attributes[SERVICE_LAST_TRIP][item]

    @property
    def available_attributes(self) -> List[str]:
        """Get the list of last-trip attributes available for this vehicle."""
        result = ['acceleration_value', 'anticipation_value', 'auxiliary_consumption_value',
                  'average_combined_consumption', 'average_electric_consumption', 'average_recuperation',
                  'date', 'driving_mode_value', 'duration', 'efficiency_value', 'electric_distance',
                  'electric_distance_ratio', 'saved_fuel', 'total_consumption_value', 'total_distance']
        return result

    @property
    @backend_parameter
    def efficiency_value(self) -> float:
        """Returns the effenciency value."""
        return float(self._state.attributes[SERVICE_LAST_TRIP]['efficiencyValue'])

    @property
    @backend_parameter
    def total_distance(self) -> float:
        """Returns the total distance."""
        return float(self._state.attributes[SERVICE_LAST_TRIP]['totalDistance'])

    @property
    @backend_parameter
    def electric_distance(self) -> float:
        """Returns the electric distance."""
        return float(self._state.attributes[SERVICE_LAST_TRIP]['electricDistance'])

    @property
    @backend_parameter
    def average_electric_consumption(self) -> float:
        """Returns the average electric consumption."""
        return float(self._state.attributes[SERVICE_LAST_TRIP]['avgElectricConsumption'])

    @property
    @backend_parameter
    def average_recuperation(self) -> float:
        """Returns the average recuperation."""
        return float(self._state.attributes[SERVICE_LAST_TRIP]['avgRecuperation'])

    @property
    @backend_parameter
    def driving_mode_value(self) -> float:
        """Returns the driving mode value."""
        return float(self._state.attributes[SERVICE_LAST_TRIP]['drivingModeValue'])

    @property
    @backend_parameter
    def acceleration_value(self) -> float:
        """Returns the acceleration value."""
        return float(self._state.attributes[SERVICE_LAST_TRIP]['accelerationValue'])

    @property
    @backend_parameter
    def anticipation_value(self) -> float:
        """Returns the anticipation value."""
        return float(self._state.attributes[SERVICE_LAST_TRIP]['anticipationValue'])

    @property
    @backend_parameter
    def total_consumption_value(self) -> float:
        """Returns the total consumption value."""
        return float(self._state.attributes[SERVICE_LAST_TRIP]['totalConsumptionValue'])

    @property
    @backend_parameter
    def auxiliary_consumption_value(self) -> float:
        """Returns the auxiliary consumption value."""
        return float(self._state.attributes[SERVICE_LAST_TRIP]['auxiliaryConsumptionValue'])

    @property
    @backend_parameter
    def average_combined_consumption(self) -> float:
        """Returns the average combined consumption."""
        return float(self._state.attributes[SERVICE_LAST_TRIP]['avgCombinedConsumption'])

    @property
    @backend_parameter
    def electric_distance_ratio(self) -> float:
        """Returns the electric distance ratio."""
        return float(self._state.attributes[SERVICE_LAST_TRIP]['electricDistanceRatio'])

    @property
    @backend_parameter
    def saved_fuel(self) -> float:
        """Returns the saved fuel."""
        return float(self._state.attributes[SERVICE_LAST_TRIP]['savedFuel'])

    @property
    @backend_parameter
    def date(self) -> str:
        """Returns the date."""
        return self._state.attributes[SERVICE_LAST_TRIP]['date']

    @property
    @backend_parameter
    def duration(self) -> float:
        """Returns the duration."""
        return float(self._state.attributes[SERVICE_LAST_TRIP]['duration'])
