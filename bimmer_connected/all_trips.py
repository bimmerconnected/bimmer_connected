"""Models the all trips of a vehicle."""

import logging

from bimmer_connected.const import SERVICE_ALL_TRIPS

_LOGGER = logging.getLogger(__name__)


def backend_parameter_statistic(func):
    """Decorator for parameters reading data from the backend.

    Errors are handled in a default way.
    """
    def _func_wrapper(self: 'StatisticValues', *args, **kwargs):
        # pylint: disable=protected-access
        try:
            return func(self, *args, **kwargs)
        except KeyError:
            _LOGGER.debug('No data available for attribute %s!', str(func))
            return None
    return _func_wrapper


class StatisticValues:
    """
    This class provides a nicer API than parsing the JSON format directly.
    """

    def __init__(self, ccm_dict: dict):
        self._ccm_dict = ccm_dict

    @property
    @backend_parameter_statistic
    def community_low(self) -> float:
        return float(self._ccm_dict["communityLow"])

    @property
    @backend_parameter_statistic
    def community_average(self) -> float:
        return float(self._ccm_dict["communityAverage"])

    @property
    @backend_parameter_statistic
    def community_high(self) -> float:
        return float(self._ccm_dict["communityHigh"])

    @property
    @backend_parameter_statistic
    def user_average(self) -> float:
        return float(self._ccm_dict["userAverage"])

    @property
    @backend_parameter_statistic
    def user_high(self) -> float:
        return float(self._ccm_dict["userHigh"])

    @property
    @backend_parameter_statistic
    def user_total(self) -> float:
        return float(self._ccm_dict["userTotal"])

    @property
    @backend_parameter_statistic
    def user_current_charge_cycle(self) -> float:
        return float(self._ccm_dict["userCurrentChargeCycle"])


def backend_parameter(func):
    """Decorator for parameters reading data from the backend.

    Errors are handled in a default way.
    """
    def _func_wrapper(self: 'AllTrips', *args, **kwargs):
        # pylint: disable=protected-access
        if self._state.attributes[SERVICE_ALL_TRIPS] is None:
            raise ValueError('No data available for vehicles trips!')
        try:
            return func(self, *args, **kwargs)
        except KeyError:
            _LOGGER.debug('No data available for attribute %s!', str(func))
            return None
    return _func_wrapper


class AllTrips:  # pylint: disable=too-many-public-methods
    """Models the all trips service of a vehicle."""

    def __init__(self, state):
        """Constructor."""
        self._state = state

    def __getattr__(self, item):
        """Generic get function for all backend attributes."""
        return self._state.attributes[SERVICE_ALL_TRIPS][item]

    @property
    @backend_parameter
    def reset_date(self) -> str:
        """Returns the average combined consumption."""
        return self._state.attributes[SERVICE_ALL_TRIPS]['resetDate']

    @property
    @backend_parameter
    def battery_size_max(self) -> int:
        """Maximal battery size, in Wh."""
        return int(self._state.attributes[SERVICE_ALL_TRIPS]['batterySizeMax'])

    @property
    @backend_parameter
    def average_electric_consumption(self) -> StatisticValues:
        """Returns the average electric consumption."""
        return StatisticValues(self._state.attributes[SERVICE_ALL_TRIPS]['avgElectricConsumption'])

    @property
    @backend_parameter
    def average_recopuration(self) -> StatisticValues:
        """Returns the average recopuration."""
        return StatisticValues(self._state.attributes[SERVICE_ALL_TRIPS]['avgRecuperation'])

    @property
    @backend_parameter
    def chargecycle_range(self) -> StatisticValues:
        """Returns the charge cycle range."""
        return StatisticValues(self._state.attributes[SERVICE_ALL_TRIPS]['chargecycleRange'])

    @property
    @backend_parameter
    def total_electric_distance(self) -> StatisticValues:
        """Returns the total electric distance."""
        return StatisticValues(self._state.attributes[SERVICE_ALL_TRIPS]['totalElectricDistance'])

    @property
    @backend_parameter
    def average_combined_consumption(self) -> StatisticValues:
        """Returns the average combined consumption."""
        return StatisticValues(self._state.attributes[SERVICE_ALL_TRIPS]['avgCombinedConsumption'])
