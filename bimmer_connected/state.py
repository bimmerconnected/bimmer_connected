"""Models the state of a vehicle."""

import logging
import datetime
from typing import List

from bimmer_connected.const import SERVICE_STATUS, VEHICLE_STATUS_URL, SERVICE_LAST_TRIP, \
    VEHICLE_STATISTICS_LAST_TRIP_URL, SERVICE_ALL_TRIPS, VEHICLE_STATISTICS_ALL_TRIPS_URL, \
    SERVICE_CHARGING_PROFILE, VEHICLE_CHARGING_PROFILE_URL, SERVICE_DESTINATIONS, VEHICLE_DESTINATIONS_URL, \
    SERVICE_RANGEMAP, VEHICLE_RANGEMAP_URL, SERVICE_EFFICIENCY, VEHICLE_EFFICIENCY, SERVICE_NAVIGATION, \
    VEHICLE_NAVIGATION

from bimmer_connected.vehicle_status import VehicleStatus, LockState, ParkingLightState, ChargingState, \
    CheckControlMessage, ConditionBasedServiceReport, Lid, Window
from bimmer_connected.last_trip import LastTrip
from bimmer_connected.all_trips import AllTrips
from bimmer_connected.charging_profile import ChargingProfile
from bimmer_connected.last_destinations import LastDestinations
from bimmer_connected.range_maps import RangeMaps
from bimmer_connected.navigation import Navigation
from bimmer_connected.efficiency import Efficiency

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
    def __init__(self, account, vehicle):
        """Constructor."""
        self._account = account
        self._vehicle = vehicle
        self._attributes = {}
        self.vehicle_status = VehicleStatus(self)
        self.all_trips = AllTrips(self)
        self.charging_profile = ChargingProfile(self)
        self.last_trip = LastTrip(self)
        self.last_destinations = LastDestinations(self)
        self.range_maps = RangeMaps(self)
        self.navigation = Navigation(self)
        self.efficiency = Efficiency(self)

        self._url = {
            SERVICE_STATUS: VEHICLE_STATUS_URL,
            SERVICE_LAST_TRIP: VEHICLE_STATISTICS_LAST_TRIP_URL,
            SERVICE_ALL_TRIPS: VEHICLE_STATISTICS_ALL_TRIPS_URL,
            SERVICE_CHARGING_PROFILE: VEHICLE_CHARGING_PROFILE_URL,
            SERVICE_DESTINATIONS: VEHICLE_DESTINATIONS_URL,
            SERVICE_RANGEMAP: VEHICLE_RANGEMAP_URL,
            SERVICE_EFFICIENCY: VEHICLE_EFFICIENCY,
            SERVICE_NAVIGATION: VEHICLE_NAVIGATION}

        self._key = {
            SERVICE_STATUS: 'vehicleStatus',
            SERVICE_LAST_TRIP: 'lastTrip',
            SERVICE_ALL_TRIPS: 'allTrips',
            SERVICE_CHARGING_PROFILE: 'weeklyPlanner',
            SERVICE_DESTINATIONS: 'destinations',
            SERVICE_RANGEMAP: 'rangemap',
            SERVICE_EFFICIENCY: '',
            SERVICE_NAVIGATION: ''}

        for service in self._url:
            self._attributes[service] = {}

    def update_data(self) -> None:
        """Read new status data from the server."""
        _LOGGER.debug('requesting new data from connected drive')
        format_string = '%Y-%m-%dT%H:%M:%S'
        timestamp = datetime.datetime.now().strftime(format_string)
        params = {
            'deviceTime': timestamp,
            'dlat': self._vehicle.observer_latitude,
            'dlon': self._vehicle.observer_longitude,
        }

        for service in self._vehicle.available_state_services:
            try:
                response = self._account.send_request(
                    self._url[service].format(server=self._account.server_url, vin=self._vehicle.vin),
                    logfilename=service, params=params)
                if not self._key[service]:
                    self._attributes[service] = response.json()
                else:
                    self._attributes[service] = response.json()[self._key[service]]
            except IOError:
                _LOGGER.debug('Service %s failed', service)

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
        return self.vehicle_status.attributes[item]

    @staticmethod
    def _parse_datetime(date_str: str) -> datetime.datetime:
        """Convert a time string into datetime."""
        date_format = "%Y-%m-%dT%H:%M:%S%z"
        return datetime.datetime.strptime(date_str, date_format)

    @property
    @backend_parameter
    def timestamp(self) -> datetime.datetime:
        """Get the timestamp when the data was recorded."""
        _LOGGER.warning("Funcion deprecated use state.vehicle_status.timestamp instead")
        return self.vehicle_status.timestamp

    @property
    @backend_parameter
    def gps_position(self) -> (float, float):
        """Get the last known position of the vehicle.

        Returns a tuple of (latitude, longitude).
        This only provides data, if the vehicle tracking is enabled!
        """
        _LOGGER.warning("Funcion deprecated use state.vehicle_status.gps_position instead")
        return self.vehicle_status.gps_position

    @property
    @backend_parameter
    def is_vehicle_tracking_enabled(self) -> bool:
        """Check if the position tracking of the vehicle is enabled.

        The server return "OK" if tracking is enabled and "DRIVER_DISABLED" if it is disabled in the vehicle.
        """
        _LOGGER.warning("Funcion deprecated use state.vehicle_status.is_vehicle_tracking_enabled instead")
        return bool(self.vehicle_status.is_vehicle_tracking_enabled)

    @property
    @backend_parameter
    def mileage(self) -> int:
        """Get the mileage of the vehicle.

        Returns a tuple of (value, unit_of_measurement)
        """
        _LOGGER.warning("Funcion deprecated use state.vehicle_status.mileage instead")
        return self.vehicle_status.mileage

    @property
    @backend_parameter
    def remaining_range_fuel(self) -> int:
        """Get the remaining range of the vehicle on fuel.

        Returns a tuple of (value, unit_of_measurement)
        """
        _LOGGER.warning("Funcion deprecated use state.vehicle_status.remaining_range_fuel instead")
        return self.vehicle_status.remaining_range_fuel

    @property
    @backend_parameter
    def remaining_fuel(self) -> int:
        """Get the remaining fuel of the vehicle.

        Returns a tuple of (value, unit_of_measurement)
        """
        _LOGGER.warning("Funcion deprecated use state.vehicle_status.remaining_fuel instead")
        return self.vehicle_status.remaining_fuel

    @property
    @backend_parameter
    def lids(self) -> List[Lid]:
        """Get all lids (doors+hatch+trunk) of the car."""
        _LOGGER.warning("Funcion deprecated use state.vehicle_status.lids instead")
        return self.vehicle_status.lids

    @property
    @backend_parameter
    def open_lids(self) -> List[Lid]:
        """Get all open lids of the car."""
        _LOGGER.warning("Funcion deprecated use state.vehicle_status.open_lids instead")
        return self.vehicle_status.open_lids

    @property
    @backend_parameter
    def all_lids_closed(self) -> bool:
        """Check if all lids are closed."""
        _LOGGER.warning("Funcion deprecated use state.vehicle_status.all_lids_closed instead")
        return self.vehicle_status.all_lids_closed

    @property
    @backend_parameter
    def windows(self) -> List[Window]:
        """Get all windows (doors+sun roof) of the car."""
        _LOGGER.warning("Funcion deprecated use state.vehicle_status.windows instead")
        return self.vehicle_status.windows

    @property
    @backend_parameter
    def open_windows(self) -> List[Window]:
        """Get all open windows of the car."""
        _LOGGER.warning("Funcion deprecated use state.vehicle_status.open_windows instead")
        return self.vehicle_status.open_windows

    @property
    @backend_parameter
    def all_windows_closed(self) -> bool:
        """Check if all windows are closed."""
        _LOGGER.warning("Funcion deprecated use state.vehicle_status.all_windows_closed instead")
        return self.vehicle_status.all_windows_closed

    @property
    @backend_parameter
    def door_lock_state(self) -> LockState:
        """Get state of the door locks."""
        _LOGGER.warning("Funcion deprecated use state.vehicle_status.all_windows_closed instead")
        return self.vehicle_status.door_lock_state

    @property
    @backend_parameter
    def last_update_reason(self) -> str:
        """The reason for the last state update"""
        _LOGGER.warning("Funcion deprecated use state.vehicle_status.last_update_reason instead")
        return self.vehicle_status.last_update_reason

    @property
    @backend_parameter
    def last_charging_end_result(self) -> str:
        """Get the last charging end result"""
        _LOGGER.warning("Funcion deprecated use state.vehicle_status.last_charging_end_result instead")
        return self.vehicle_status.last_charging_end_result

    @property
    @backend_parameter
    def connection_status(self) -> str:
        """Get status of the connection"""
        _LOGGER.warning("Funcion deprecated use state.vehicle_status.connection_status instead")
        return self.vehicle_status.connection_status

    @property
    @backend_parameter
    def condition_based_services(self) -> List[ConditionBasedServiceReport]:
        """Get status of the condition based services."""
        _LOGGER.warning("Funcion deprecated use state.vehicle_status.condition_based_services instead")
        return self.vehicle_status.condition_based_services

    @property
    @backend_parameter
    def are_all_cbs_ok(self) -> bool:
        """Check if the status of all condition based services is "OK"."""
        _LOGGER.warning("Funcion deprecated use state.vehicle_status.are_all_cbs_ok instead")
        return bool(self.vehicle_status.are_all_cbs_ok)

    @property
    @backend_parameter
    def parking_lights(self) -> ParkingLightState:
        """Get status of parking lights.

        :returns None if status is unknown.
        """
        _LOGGER.warning("Funcion deprecated use state.vehicle_status.parking_lights instead")
        return self.vehicle_status.parking_lights

    @property
    @backend_parameter
    def are_parking_lights_on(self) -> bool:
        """Get status of parking lights.

        :returns None if status is unknown.
        """
        _LOGGER.warning("Funcion deprecated use state.vehicle_status.are_parking_lights_on instead")
        return bool(self.vehicle_status.are_parking_lights_on)

    @property
    @backend_parameter
    def remaining_range_electric(self) -> int:
        """Remaining range on battery, in kilometers."""
        _LOGGER.warning("Funcion deprecated use state.vehicle_status.remaining_range_electric instead")
        return self.vehicle_status.remaining_range_electric

    @property
    @backend_parameter
    def remaining_range_total(self) -> int:
        """Get the total remaining range of the vehicle in kilometers.

        That is electrical range + fuel range.
        """
        _LOGGER.warning("Funcion deprecated use state.vehicle_status.remaining_range_total instead")
        return self.vehicle_status.remaining_range_total

    @property
    @backend_parameter
    def max_range_electric(self) -> int:
        """ This can change with driving style and temperature in kilometers."""
        _LOGGER.warning("Funcion deprecated use state.vehicle_status.max_range_electric instead")
        return self.vehicle_status.max_range_electric

    @property
    @backend_parameter
    def charging_status(self) -> ChargingState:
        """Charging state of the vehicle."""
        _LOGGER.warning("Funcion deprecated use state.vehicle_status.charging_status instead")
        return self.vehicle_status.charging_status

    @property
    @backend_parameter
    def charging_time_remaining(self) -> datetime.timedelta:
        """Get the remaining charging time."""
        _LOGGER.warning("Funcion deprecated use state.vehicle_status.charging_time_remaining instead")
        return self.vehicle_status.charging_time_remaining

    @property
    @backend_parameter
    def charging_level_hv(self) -> int:
        """State of charge of the high voltage battery in percent."""
        _LOGGER.warning("Funcion deprecated use state.vehicle_status.charging_level_hv instead")
        return self.vehicle_status.charging_level_hv

    @property
    @backend_parameter
    def check_control_messages(self) -> List[CheckControlMessage]:
        """List of check control messages."""
        _LOGGER.warning("Funcion deprecated use state.vehicle_status.check_control_messages instead")
        return self.vehicle_status.check_control_messages

    @property
    @backend_parameter
    def has_check_control_messages(self) -> bool:
        """Return true if any check control message is present."""
        _LOGGER.warning("Funcion deprecated use state.vehicle_status.has_check_control_messages instead")
        return bool(self.vehicle_status.has_check_control_messages)
