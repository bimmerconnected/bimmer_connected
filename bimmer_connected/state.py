"""Models the state of a vehicle."""

import logging
import datetime
from typing import List
from enum import Enum

from bimmer_connected.const import SERVICE_STATUS, VEHICLE_STATUS_URL, SERVICE_LAST_TRIP, \
    VEHICLE_STATISTICS_LAST_TRIP_URL, SERVICE_ALL_TRIPS, VEHICLE_STATISTICS_ALL_TRIPS_URL, \
    SERVICE_CHARGING_PROFILE, VEHICLE_CHARGING_PROFILE_URL, SERVICE_DESTINATIONS, VEHICLE_DESTINATIONS_URL, \
    SERVICE_RANGEMAP, VEHICLE_RANGEMAP_URL

from bimmer_connected.vehicle_status import VehicleStatus
from bimmer_connected.vehicle_status import LockState
from bimmer_connected.vehicle_status import ParkingLightState
from bimmer_connected.vehicle_status import ChargingState
from bimmer_connected.vehicle_status import CheckControlMessage
from bimmer_connected.last_trip import LastTrip
from bimmer_connected.all_trips import AllTrips
from bimmer_connected.charging_profile import ChargingProfile
from bimmer_connected.last_destinations import LastDestinations
from bimmer_connected.range_maps import RangeMaps

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


class VehicleState:  # pylint: disable=too-many-public-methods
    """Models the state of a vehicle."""

    def __init__(self, account, vehicle):
        """Constructor."""
        self._account = account
        self._vehicle = vehicle
        self._attributes = {}
        self.vehicle_status = None
        self.all_trips = None
        self.charging_profile = None
        self.vehicle_status = VehicleStatus(self)
        self.all_trips = AllTrips(self)
        self.charging_profile = ChargingProfile(self)
        self.last_trip = LastTrip(self)
        self.last_destinations = LastDestinations(self)
        self.range_maps = RangeMaps(self)
  
        self._url = {
            SERVICE_STATUS : VEHICLE_STATUS_URL,
            SERVICE_LAST_TRIP : VEHICLE_STATISTICS_LAST_TRIP_URL,
            SERVICE_ALL_TRIPS : VEHICLE_STATISTICS_ALL_TRIPS_URL,
            SERVICE_CHARGING_PROFILE : VEHICLE_CHARGING_PROFILE_URL,
            SERVICE_DESTINATIONS : VEHICLE_DESTINATIONS_URL,
            SERVICE_RANGEMAP : VEHICLE_RANGEMAP_URL}

        self._key = {
            SERVICE_STATUS : 'vehicleStatus',
            SERVICE_LAST_TRIP : 'lastTrip',
            SERVICE_ALL_TRIPS : 'allTrips',
            SERVICE_CHARGING_PROFILE : 'weeklyPlanner',
            SERVICE_DESTINATIONS : 'destinations',
            SERVICE_RANGEMAP : 'rangemap'}

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

        for service in self._url:
            try:
                response = self._account.send_request(
                    self._url[service].format(server=self._account.server_url, vin=self._vehicle.vin), logfilename=service,
                    params=params)
                self._attributes[service] = response.json()[self._key[service]]
            except:
                _LOGGER.debug('Service ' + service + ' failed')

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
        return self._attributes[item]

    @staticmethod
    def _parse_datetime(date_str: str) -> datetime.datetime:
        _LOGGER.info("Funcion depreceted use state.vehicle_status._parse_datetime instead")
        return VehicleStatus._parse_datetime(date_str)

    @property
    @backend_parameter
    def timestamp(self) -> datetime.datetime:
        _LOGGER.info("Funcion depreceted use state.vehicle_status.timestamp instead")
        return self.vehicle_status.timestamp

    @property
    @backend_parameter
    def gps_position(self) -> (float, float):
        _LOGGER.info("Funcion depreceted use state.vehicle_status.gps_position instead")
        return self.vehicle_status.gps_position

    @property
    @backend_parameter
    def is_vehicle_tracking_enabled(self) -> bool:
        _LOGGER.info("Funcion depreceted use state.vehicle_status.is_vehicle_tracking_enabled instead")
        return bool(self.vehicle_status.is_vehicle_tracking_enabled)

    @property
    @backend_parameter
    def mileage(self) -> int:
        _LOGGER.info("Funcion depreceted use state.vehicle_status.mileage instead")
        return self.vehicle_status.mileage

    @property
    @backend_parameter
    def remaining_range_fuel(self) -> int:
        _LOGGER.info("Funcion depreceted use state.vehicle_status.remaining_range_fuel instead")
        return self.vehicle_status.remaining_range_fuel

    @property
    @backend_parameter
    def remaining_fuel(self) -> int:
        _LOGGER.info("Funcion depreceted use state.vehicle_status.remaining_fuel instead")
        return self.vehicle_status.remaining_fuel

    @property
    @backend_parameter
    def lids(self) -> List['Lid']:
        _LOGGER.info("Funcion depreceted use state.vehicle_status.lids instead")
        return self.vehicle_status.lids

    @property
    @backend_parameter
    def open_lids(self) -> List['Lid']:
        _LOGGER.info("Funcion depreceted use state.vehicle_status.open_lids instead")
        return self.vehicle_status.open_lids

    @property
    @backend_parameter
    def all_lids_closed(self) -> bool:
        _LOGGER.info("Funcion depreceted use state.vehicle_status.all_lids_closed instead")
        return self.vehicle_status.all_lids_closed

    @property
    @backend_parameter
    def windows(self) -> List['Window']:
        _LOGGER.info("Funcion depreceted use state.vehicle_status.windows instead")
        return self.vehicle_status.windows

    @property
    @backend_parameter
    def open_windows(self) -> List['Window']:
        _LOGGER.info("Funcion depreceted use state.vehicle_status.open_windows instead")
        return self.vehicle_status.open_windows

    @property
    @backend_parameter
    def all_windows_closed(self) -> bool:
        _LOGGER.info("Funcion depreceted use state.vehicle_status.all_windows_closed instead")
        return self.vehicle_status.all_windows_closed

    @property
    @backend_parameter
    def door_lock_state(self) -> LockState:
        _LOGGER.info("Funcion depreceted use state.vehicle_status.all_windows_closed instead")
        return self.vehicle_status.door_lock_state

    @property
    @backend_parameter
    def last_update_reason(self) -> str:
        _LOGGER.info("Funcion depreceted use state.vehicle_status.last_update_reason instead")
        return self.vehicle_status.last_update_reason

    @property
    @backend_parameter
    def last_charging_end_result(self) -> str:
        _LOGGER.info("Funcion depreceted use state.vehicle_status.last_charging_end_result instead")
        return self.vehicle_status.last_charging_end_result

    @property
    @backend_parameter
    def connection_status(self) -> str:
        _LOGGER.info("Funcion depreceted use state.vehicle_status.connection_status instead")
        return self.vehicle_status.connection_status

    @property
    @backend_parameter
    def condition_based_services(self) -> List['ConditionBasedServiceReport']:
        _LOGGER.info("Funcion depreceted use state.vehicle_status.condition_based_services instead")
        return self.vehicle_status.condition_based_services

    @property
    @backend_parameter
    def are_all_cbs_ok(self) -> bool:
        _LOGGER.info("Funcion depreceted use state.vehicle_status.are_all_cbs_ok instead")
        return bool(self.vehicle_status.are_all_cbs_ok)

    @property
    @backend_parameter
    def parking_lights(self) -> ParkingLightState:
        _LOGGER.info("Funcion depreceted use state.vehicle_status.parking_lights instead")
        return self.vehicle_status.parking_lights

    @property
    @backend_parameter
    def are_parking_lights_on(self) -> bool:
        _LOGGER.info("Funcion depreceted use state.vehicle_status.are_parking_lights_on instead")
        return bool(self.vehicle_status.are_parking_lights_on)

    @property
    @backend_parameter
    def remaining_range_electric(self) -> int:
        _LOGGER.info("Funcion depreceted use state.vehicle_status.remaining_range_electric instead")
        return self.vehicle_status.remaining_range_electric

    @property
    @backend_parameter
    def remaining_range_total(self) -> int:
        _LOGGER.info("Funcion depreceted use state.vehicle_status.remaining_range_total instead")
        return self.vehicle_status.remaining_range_total

    @property
    @backend_parameter
    def max_range_electric(self) -> int:
        _LOGGER.info("Funcion depreceted use state.vehicle_status.max_range_electric instead")
        return self.vehicle_status.max_range_electric

    @property
    @backend_parameter
    def charging_status(self) -> ChargingState:
        _LOGGER.info("Funcion depreceted use state.vehicle_status.charging_status instead")
        return self.vehicle_status.charging_status

    @property
    @backend_parameter
    def charging_time_remaining(self) -> datetime.timedelta:
        _LOGGER.info("Funcion depreceted use state.vehicle_status.charging_time_remaining instead")
        return self.vehicle_status.charging_time_remaining

    @property
    @backend_parameter
    def charging_level_hv(self) -> int:
        _LOGGER.info("Funcion depreceted use state.vehicle_status.charging_level_hv instead")
        return self.vehicle_status.charging_level_hv

    @property
    @backend_parameter
    def check_control_messages(self) -> List[CheckControlMessage]:
        _LOGGER.info("Funcion depreceted use state.vehicle_status.check_control_messages instead")
        return self.vehicle_status.check_control_messages

    @property
    @backend_parameter
    def has_check_control_messages(self) -> bool:
        _LOGGER.info("Funcion depreceted use state.vehicle_status.has_check_control_messages instead")
        return bool(self.vehicle_status.has_check_control_messages)


