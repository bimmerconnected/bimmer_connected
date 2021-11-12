"""Models the state of a vehicle."""

import logging
import datetime
from typing import TYPE_CHECKING

# from bimmer_connected.const import SERVICE_STATUS, VEHICLE_STATUS_URL, SERVICE_LAST_TRIP, \
#     , SERVICE_ALL_TRIPS, VEHICLE_STATISTICS_ALL_TRIPS_URL, \
#     SERVICE_CHARGING_PROFILE, VEHICLE_CHARGING_PROFILE_URL, SERVICE_DESTINATIONS, VEHICLE_DESTINATIONS_URL, \
#     SERVICE_RANGEMAP, VEHICLE_RANGEMAP_URL, SERVICE_EFFICIENCY, VEHICLE_EFFICIENCY, SERVICE_NAVIGATION, \
#     VEHICLE_NAVIGATION

from bimmer_connected.vehicle_status import VehicleStatus
# from bimmer_connected.charging_profile import ChargingProfile


if TYPE_CHECKING:
    from bimmer_connected.account import ConnectedDriveAccount
    from bimmer_connected.vehicle import ConnectedDriveVehicle

_LOGGER = logging.getLogger(__name__)


def backend_parameter(func):
    """Decorator for parameters reading data from the backend.

    Errors are handled in a default way.
    """
    def _func_wrapper(self: 'VehicleState', *args, **kwargs):
        # pylint: disable=protected-access
        if self._attributes is None:
            raise ValueError('No data available for vehicles state!')
        try:
            return func(self, *args, **kwargs)
        except KeyError:
            _LOGGER.debug('No data available for attribute %s!', str(func))
            return None
    return _func_wrapper


class VehicleState:
    """Models the state of a vehicle."""

    # pylint: disable=too-many-public-methods
    # pylint: disable=too-many-instance-attributes
    # Nine is reasonable in this case.
    def __init__(self, account: "ConnectedDriveAccount", vehicle: "ConnectedDriveVehicle"):
        """Constructor."""
        self._account = account
        self._vehicle = vehicle
        self._attributes = {}  # type: dict[str, dict]
        self.vehicle_status = VehicleStatus(vehicle)

        self._url = {
            # SERVICE_CHARGING_PROFILE: VEHICLE_CHARGING_PROFILE_URL,
        }

        self._key = {
            # SERVICE_PROPERTIES: 'vehicleStatus',
            # SERVICE_LAST_TRIP: 'lastTrip',
            # SERVICE_ALL_TRIPS: 'allTrips',
            # SERVICE_CHARGING_PROFILE: 'weeklyPlanner',
            # SERVICE_DESTINATIONS: 'destinations',
            # SERVICE_RANGEMAP: 'rangemap',
            # SERVICE_EFFICIENCY: '',
            # SERVICE_NAVIGATION: ''
        }

        for service in self._url:
            self._attributes[service] = {}

    def update_data(self) -> None:
        """Read new status data from the server."""
        _LOGGER.debug('requesting new data from connected drive')

        # TODO: This needs major rework. Each service has a single URL and vehicle selection
        #       is done by sending a JSON body.
        #       
        #       However currently we have only one status call and have to figure out what to do
        #       with `charging-sessions` and `charging-characteristics`

        # format_string = '%Y-%m-%dT%H:%M:%S'
        # timestamp = datetime.datetime.now().strftime(format_string)
        # params = {
        #     'deviceTime': timestamp,
        #     'dlat': self._vehicle.observer_latitude,
        #     'dlon': self._vehicle.observer_longitude,
        # }
        #
        # for service in self._vehicle.available_state_services:
        #     try:
        #         response = self._account.send_request(
        #             self._url[service].format(server=self._account._server_url, vin=self._vehicle.vin),
        #             logfilename=service, params=params)
        #         if not self._key[service]:
        #             self._attributes[service] = response.json()
        #         else:
        #             self._attributes[service] = response.json()[self._key[service]]
        #     except IOError:
        #         _LOGGER.debug('Service %s failed', service)
        #     except KeyError:  # When JSON contains no service-key
        #         _LOGGER.debug('Service %s failed', service)

        _LOGGER.debug(self._attributes)
        _LOGGER.debug('received new data from connected drive')

    @property
    @backend_parameter
    def attributes(self) -> dict:
        """Retrieve all attributes from the sever.

        This does not parse the results in any way.
        """
        return self._attributes

    def __getattr__(self, item):
        """Generic get function for all backend attributes."""
        return self.vehicle_status.get(item)

    @staticmethod
    def _parse_datetime(date_str: str) -> datetime.datetime:
        """Convert a time string into datetime."""
        date_format = "%Y-%m-%dT%H:%M:%S%z"
        return datetime.datetime.strptime(date_str, date_format)
