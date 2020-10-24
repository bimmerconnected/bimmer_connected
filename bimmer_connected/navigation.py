"""Models the navigation of a vehicle."""

import logging

from bimmer_connected.const import SERVICE_NAVIGATION

_LOGGER = logging.getLogger(__name__)


def backend_parameter(func):
    """Decorator for parameters reading data from the backend.

    Errors are handled in a default way.
    """
    def _func_wrapper(self: 'Navigation', *args, **kwargs):
        # pylint: disable=protected-access
        if self._state.attributes[SERVICE_NAVIGATION] is None:
            raise ValueError('No data available for vehicles navigation!')
        try:
            return func(self, *args, **kwargs)
        except KeyError:
            _LOGGER.debug('No data available for attribute %s!', str(func))
            return None
    return _func_wrapper


class Navigation:  # pylint: disable=too-many-public-methods
    """Models the navigation of a vehicle."""

    def __init__(self, state):
        """Constructor."""
        self._state = state

    @property
    @backend_parameter
    def attributes(self) -> dict:
        """Retrieve all attributes from the sever.

        This does not parse the results in any way.
        """
        return self._state.attributes[SERVICE_NAVIGATION]

    def __getattr__(self, item):
        """Generic get function for all backend attributes."""
        return self._state.attributes[SERVICE_NAVIGATION][item]

    @property
    @backend_parameter
    def latitude(self) -> float:
        """Returns the latitude."""
        return float(self._state.attributes[SERVICE_NAVIGATION]['latitude'])

    @property
    @backend_parameter
    def longitude(self) -> float:
        """Returns the longitude."""
        return float(self._state.attributes[SERVICE_NAVIGATION]['longitude'])

    @property
    @backend_parameter
    def iso_country_code(self) -> str:
        """Returns the iso country code."""
        return self._state.attributes[SERVICE_NAVIGATION]['isoCountryCode']

    @property
    @backend_parameter
    def aux_power_regular(self) -> float:
        """Returns the aux power regular consumption."""
        return float(self._state.attributes[SERVICE_NAVIGATION]['auxPowerRegular'])

    @property
    @backend_parameter
    def aux_power_eco_pro(self) -> float:
        """Returns the aux power eco pro consumption."""
        return float(self._state.attributes[SERVICE_NAVIGATION]['auxPowerEcoPro'])

    @property
    @backend_parameter
    def aux_power_eco_pro_plus(self) -> float:
        """Returns the aux power eco pro plus consumption."""
        return float(self._state.attributes[SERVICE_NAVIGATION]['auxPowerEcoProPlus'])

    @property
    @backend_parameter
    def soc(self) -> float:
        """Returns the soc."""
        return float(self._state.attributes[SERVICE_NAVIGATION]['soc'])

    @property
    @backend_parameter
    def soc_max(self) -> float:
        """Returns the soc max."""
        try:
            return float(self._state.attributes[SERVICE_NAVIGATION]['socMax'])
        except KeyError:
            return float(self._state.attributes[SERVICE_NAVIGATION]['socmax'])

    @property
    @backend_parameter
    def eco(self) -> str:
        """Returns the eco."""
        return self._state.attributes[SERVICE_NAVIGATION]['eco']

    @property
    @backend_parameter
    def norm(self) -> str:
        """Returns the norm."""
        return self._state.attributes[SERVICE_NAVIGATION]['norm']

    @property
    @backend_parameter
    def eco_ev(self) -> str:
        """Returns the eco ev."""
        return self._state.attributes[SERVICE_NAVIGATION]['ecoEv']

    @property
    @backend_parameter
    def norm_ev(self) -> str:
        """Returns the norm ev."""
        return self._state.attributes[SERVICE_NAVIGATION]['normEv']

    @property
    @backend_parameter
    def vehicle_mass(self) -> int:
        """Returns the vehicle mass."""
        return int(self._state.attributes[SERVICE_NAVIGATION]['vehicleMass'])

    @property
    @backend_parameter
    def k_acc_reg(self) -> int:
        """Returns the k acc reg."""
        return int(self._state.attributes[SERVICE_NAVIGATION]['kAccReg'])

    @property
    @backend_parameter
    def k_dec_reg(self) -> int:
        """Returns the k dec reg."""
        return int(self._state.attributes[SERVICE_NAVIGATION]['kDecReg'])

    @property
    @backend_parameter
    def k_acc_eco(self) -> int:
        """Returns the k acc eco."""
        return int(self._state.attributes[SERVICE_NAVIGATION]['kAccEco'])

    @property
    @backend_parameter
    def k_dec_eco(self) -> int:
        """Returns the k dec eco."""
        return int(self._state.attributes[SERVICE_NAVIGATION]['kDecEco'])

    @property
    @backend_parameter
    def k_up(self) -> int:
        """Returns the k up."""
        return int(self._state.attributes[SERVICE_NAVIGATION]['kUp'])

    @property
    @backend_parameter
    def k_down(self) -> int:
        """Returns the k down."""
        return int(self._state.attributes[SERVICE_NAVIGATION]['kDown'])

    @property
    @backend_parameter
    def drive_train(self) -> str:
        """Returns the drive_train."""
        return self._state.attributes[SERVICE_NAVIGATION]['driveTrain']

    @property
    @backend_parameter
    def pending_update(self) -> bool:
        """Returns the pending update state."""
        return bool(self._state.attributes[SERVICE_NAVIGATION]['pendingUpdate'])

    @property
    @backend_parameter
    def vehicle_tracking(self) -> bool:
        """Returns the vehicle tracking state."""
        return bool(self._state.attributes[SERVICE_NAVIGATION]['vehicleTracking'])
