"""Models state and remote services of one vehicle."""
import datetime
import logging
from typing import TYPE_CHECKING, Dict, List

from bimmer_connected.api.client import MyBMWClient
from bimmer_connected.const import SERVICE_PROPERTIES, SERVICE_STATUS, VEHICLE_IMAGE_URL, CarBrands
from bimmer_connected.utils import SerializableBaseClass, get_class_property_names, serialize_for_json
from bimmer_connected.vehicle.charging_profile import ChargingProfile
from bimmer_connected.vehicle.doors_windows import DoorsAndWindows
from bimmer_connected.vehicle.fuel_indicators import FuelIndicators
from bimmer_connected.vehicle.models import GPSPosition, ValueWithUnit, StrEnum
from bimmer_connected.vehicle.position import VehiclePosition
from bimmer_connected.vehicle.remote_services import RemoteServices
from bimmer_connected.utils import parse_datetime
from bimmer_connected.vehicle.reports import CheckControlMessageReport, ConditionBasedServiceReport
from bimmer_connected.vehicle.vehicle_status import VehicleStatus
from bimmer_connected.vehicle.const import ChargingState

if TYPE_CHECKING:
    from bimmer_connected.account import ConnectedDriveAccount
    from bimmer_connected.vehicle.doors_windows import Lid, LockState, Window
    from bimmer_connected.vehicle.reports import CheckControlMessage, ConditionBasedService


_LOGGER = logging.getLogger(__name__)


class DriveTrainType(StrEnum):
    """Different types of drive trains."""
    COMBUSTION = 'COMBUSTION'
    PLUGIN_HYBRID = 'PLUGIN_HYBRID'  # PHEV
    ELECTRIC = 'ELECTRIC'
    HYBRID = 'HYBRID'  # mild hybrids


#: Set of drive trains that have a combustion engine
COMBUSTION_ENGINE_DRIVE_TRAINS = {DriveTrainType.COMBUSTION, DriveTrainType.PLUGIN_HYBRID}

#: set of drive trains that have a high voltage battery
HV_BATTERY_DRIVE_TRAINS = {DriveTrainType.PLUGIN_HYBRID, DriveTrainType.ELECTRIC}


class VehicleViewDirection(StrEnum):
    """Viewing angles for the vehicle.

    This is used to get a rendered image of the vehicle.
    """
    FRONTSIDE = 'VehicleStatus'
    FRONT = 'VehicleInfo'
    # REARSIDE = 'REARSIDE'
    # REAR = 'REAR'
    SIDE = 'ChargingHistory'
    # DASHBOARD = 'DASHBOARD'
    # DRIVERDOOR = 'DRIVERDOOR'
    # REARBIRDSEYE = 'REARBIRDSEYE'


class LscType(StrEnum):
    """Known Values for lsc_type field.

    Not really sure, what this value really contains.
    """
    NOT_CAPABLE = 'NOT_CAPABLE'
    NOT_SUPPORTED = 'NOT_SUPPORTED'
    ACTIVATED = 'ACTIVATED'


# pylint: disable=too-many-public-methods,too-many-instance-attributes
class ConnectedDriveVehicle(SerializableBaseClass):
    """Models state and remote services of one vehicle.

    :param account: ConnectedDrive account this vehicle belongs to
    :param attributes: attributes of the vehicle as provided by the server
    """

    def __init__(self, account: "ConnectedDriveAccount", vehicle_data: dict) -> None:
        self.account = account
        self.data = vehicle_data
        self.attributes = None
        self.status = VehicleStatus(self)
        self.remote_services = RemoteServices(self)
        self.fuel_indicators: FuelIndicators = FuelIndicators()
        self.vehicle_position: VehiclePosition = VehiclePosition(vehicle_region=account.region)
        self.doors_and_windows: DoorsAndWindows = DoorsAndWindows()
        self.condition_based_service_report: ConditionBasedServiceReport = ConditionBasedServiceReport()
        self.check_control_message_report: CheckControlMessageReport = CheckControlMessageReport()

        self.update_state(vehicle_data)

    def update_state(self, vehicle_data) -> None:
        """Update the state of a vehicle."""
        self.attributes = {k: v for k, v in vehicle_data.items() if k not in [SERVICE_STATUS, SERVICE_PROPERTIES]}
        self.fuel_indicators.update_from_vehicle_data(vehicle_data)
        self.vehicle_position.update_from_vehicle_data(vehicle_data)
        self.doors_and_windows.update_from_vehicle_data(vehicle_data)
        self.condition_based_service_report.update_from_vehicle_data(vehicle_data)
        self.check_control_message_report.update_from_vehicle_data(vehicle_data)

    @property
    def _status(self) -> Dict:
        """A shortcut to `data.status`."""
        return self.data[SERVICE_STATUS]

    @property
    def _properties(self) -> Dict:
        """A shortcut to `data.properties`."""
        return self.data[SERVICE_PROPERTIES]

    @property
    def charging_profile(self) -> ChargingProfile:
        """Return the charging profile if available."""
        return ChargingProfile(self.status) if self.has_weekly_planner_service else None

    @property
    def drive_train(self) -> DriveTrainType:
        """Get the type of drive train of the vehicle."""
        return DriveTrainType(self.attributes['driveTrain'])

    @property
    def name(self) -> str:
        """Get the name of the vehicle."""
        return self.attributes['model']

    @property
    def brand(self) -> CarBrands:
        """Get the car brand."""
        return CarBrands(self.attributes["brand"])

    @property
    def mileage(self) -> ValueWithUnit:
        """Get the mileage of the vehicle."""
        return ValueWithUnit(
            self._status['currentMileage']['mileage'],
            self._status['currentMileage']['units']
        )

    @property
    def has_hv_battery(self) -> bool:
        """Return True if vehicle is equipped with a high voltage battery.

        In this case we can get the state of the battery in the state attributes.
        """
        return self.drive_train in HV_BATTERY_DRIVE_TRAINS

    @property
    def has_range_extender(self) -> bool:
        """Return True if vehicle is equipped with a range extender.

        In this case we can get the state of the gas tank."""
        return self.drive_train == DriveTrainType.ELECTRIC and self.status.fuel_indicator_count == 3

    @property
    def has_internal_combustion_engine(self) -> bool:
        """Return True if vehicle is equipped with an internal combustion engine.

        In this case we can get the state of the gas tank."""
        return self.drive_train in COMBUSTION_ENGINE_DRIVE_TRAINS

    @property
    def has_weekly_planner_service(self) -> bool:
        """Return True if charging control (weekly planner) is available."""
        return self.attributes["capabilities"]["isChargingPlanSupported"]

    @property
    def is_vehicle_tracking_enabled(self) -> bool:
        """Return True if vehicle finder is enabled in vehicle."""
        return self.attributes["capabilities"]["vehicleFinder"]["isEnabled"]

    @property
    def drive_train_attributes(self) -> List[str]:
        """Get list of attributes available for the drive train of the vehicle.

        The list of available attributes depends if on the type of drive train.
        Some attributes only exist for electric/hybrid vehicles, others only if you
        have a combustion engine. Depending on the state of the vehicle, some of
        the attributes might still be None.
        """
        result = ['remaining_range_total', 'mileage']
        if self.has_hv_battery:
            result += ['charging_time_remaining', 'charging_start_time', 'charging_end_time', 'charging_time_label',
                       'charging_status', 'charging_level_hv', 'connection_status', 'remaining_range_electric',
                       'last_charging_end_result']
        if self.has_internal_combustion_engine or self.has_range_extender:
            result += ['remaining_fuel', 'remaining_range_fuel', 'fuel_percent']
        return result

    @property
    def lsc_type(self) -> LscType:
        """Get the lscType of the vehicle.

        Not really sure what that value really means. If it is NOT_CAPABLE, that probably means that the
        vehicle state will not contain much data.
        """
        return LscType(self.attributes["capabilities"]["lastStateCall"].get('lscState'))

    @property
    def available_attributes(self) -> List[str]:
        """Get the list of non-drivetrain attributes available for this vehicle."""
        # attributes available in all vehicles
        result = ['gps_position', 'vin']
        if self.lsc_type == LscType.ACTIVATED:
            # generic attributes if lsc_type =! NOT_SUPPORTED
            result += self.drive_train_attributes
            result += ['condition_based_services', 'check_control_messages', 'door_lock_state', 'timestamp',
                       'last_update_reason']
            # required for existing Home Assistant binary sensors
            result += ['lids', 'windows']
        return result

    @property
    def available_state_services(self) -> List[str]:
        """Get the list of all available state services for this vehicle."""
        result = [SERVICE_STATUS]

        return result

    # # # # # # # # # # # # # # #
    # Generic attributes
    # # # # # # # # # # # # # # #

    @property
    def timestamp(self) -> datetime.datetime:
        """Get the timestamp when the data was recorded."""
        timestamps = [ts for ts in [
            parse_datetime(self._properties.get('lastUpdatedAt')),
            parse_datetime(self._status.get('lastUpdatedAt')),
        ] if ts]
        if len(timestamps) == 0:
            return None
        return max(timestamps)

    @property
    def last_update_reason(self) -> str:
        """The reason for the last state update"""
        return self._status['timestampMessage']

    @property
    def is_vehicle_active(self) -> bool:
        """Check if the vehicle is active/moving.

        If the vehicle was active/moving at the time of the last status update, current position is not available.
        """
        return self._properties['inMotion']

    # # # # # # # # # # # # # # #
    # Vehicle position
    # # # # # # # # # # # # # # #

    @property
    def gps_position(self) -> GPSPosition:
        """Get the last known position of the vehicle.

        Only provides data if vehicle tracking is enabled!
        """
        if not self.vehicle_position:
            return GPSPosition(None, None)
        return GPSPosition(
            self.vehicle_position.latitude,
            self.vehicle_position.longitude
        )

    @property
    def gps_heading(self) -> int:
        """Get the last known heading/direction of the vehicle.

        Only provides data if vehicle tracking is enabled!
        """
        if not self.vehicle_position:
            return None
        return self.vehicle_position.heading

    # # # # # # # # # # # # # # #
    # Fuel indicators & similar
    # # # # # # # # # # # # # # #
    @property
    def fuel_indicator_count(self) -> int:
        """Gets the number of fuel indicators.

        Can be used to identify REX vehicles if driveTrain == ELECTRIC.
        """
        return len(self._status["fuelIndicators"])

    @property
    def remaining_range_fuel(self) -> ValueWithUnit:
        """Get the remaining range of the vehicle on fuel."""
        return self.fuel_indicators.remaining_range_fuel

    @property
    def remaining_range_electric(self) -> ValueWithUnit:
        """Get the remaining range of the vehicle on electricity."""
        return self.fuel_indicators.remaining_range_electric

    @property
    def remaining_range_total(self) -> ValueWithUnit:
        """Get the total remaining range of the vehicle (fuel + electricity, if available)."""
        return self.fuel_indicators.remaining_range_combined

    @property
    def remaining_fuel(self) -> ValueWithUnit:
        """Get the remaining fuel of the vehicle."""
        return ValueWithUnit(
            self._properties["fuelLevel"]["value"],
            self._properties["fuelLevel"]["units"],
        )

    @property
    def remaining_battery_percent(self) -> int:
        """State of charge of the high voltage battery in percent."""
        return int(
            self._properties["electricRangeAndStatus"]["chargePercentage"]
        )

    @property
    def remaining_fuel_percent(self) -> int:
        """State of charge of the high voltage battery in percent."""
        return int(
            self._properties["fuelPercentage"]["value"]
        )

    # # # # # # # # # # # # # # #
    # Charging information
    # # # # # # # # # # # # # # #
    @property
    def charging_status(self) -> ChargingState:
        """Charging state of the vehicle."""
        if "chargingState" not in self._properties:
            return None
        return ChargingState(self.fuel_indicators.charging_status)

    @property
    def charging_time_start(self) -> datetime.datetime:
        """The planned time the vehicle will start charging."""
        if self.fuel_indicators.charging_start_time:
            return self.fuel_indicators.charging_start_time.replace(tzinfo=self.account.timezone)
        return None

    @property
    def charging_time_end(self) -> datetime.datetime:
        """The estimated time the vehicle will have finished charging."""
        if self.fuel_indicators.charging_end_time:
            return self.fuel_indicators.charging_end_time.replace(tzinfo=self.account.timezone)
        return None

    @property
    def charging_time_label(self) -> str:
        """The planned start/estimated end time as provided by the API."""
        return self.fuel_indicators.charging_time_label

    @property
    def connection_status(self) -> str:
        """Get status of the connection"""
        if "chargingState" not in self._properties:
            return None
        return (
            "CONNECTED"
            if self._properties["chargingState"]["isChargerConnected"]
            else "DISCONNECTED"
        )

    # # # # # # # # # # # # # # #
    # Doors and windows
    # # # # # # # # # # # # # # #

    @property
    def lids(self) -> List['Lid']:
        """Get all lids (doors+hatch+trunk) of the car."""
        return self.doors_and_windows.lids

    @property
    def open_lids(self) -> List['Lid']:
        """Get all open lids of the car."""
        return [lid for lid in self.lids if not lid.is_closed]

    @property
    def all_lids_closed(self) -> bool:
        """Check if all lids are closed."""
        return len(self.open_lids) == 0

    @property
    def windows(self) -> List['Window']:
        """Get all windows (doors+sunroof) of the car."""
        return self.doors_and_windows.windows

    @property
    def open_windows(self) -> List['Window']:
        """Get all open windows of the car."""
        return [lid for lid in self.windows if not lid.is_closed]

    @property
    def all_windows_closed(self) -> bool:
        """Check if all windows are closed."""
        return len(self.open_windows) == 0

    @property
    def door_lock_state(self) -> "LockState":
        """Get state of the door locks."""
        return self.doors_and_windows.door_lock_state

    # # # # # # # # # # # # # # #
    # Condition Based & Service reports
    # # # # # # # # # # # # # # #

    @property
    def condition_based_services(self) -> List["ConditionBasedService"]:
        """Get status of the condition based services."""
        return self.condition_based_service_report.reports

    @property
    def are_all_cbs_ok(self) -> bool:
        """Check if the status of all condition based services are "OK"."""
        return not self.condition_based_service_report.is_service_required

    @property
    def check_control_messages(self) -> List["CheckControlMessage"]:
        """List of check control messages."""
        return self.check_control_message_report.reports

    @property
    def has_check_control_messages(self) -> bool:
        """Return true if any check control message is present."""
        return self.check_control_message_report.has_check_control_messages

    # # # # # # # # # # # # # # #
    # Generic functions
    # # # # # # # # # # # # # # #

    async def get_vehicle_image(self, direction: VehicleViewDirection) -> bytes:
        """Get a rendered image of the vehicle.

        :returns bytes containing the image in PNG format.
        """
        url = VEHICLE_IMAGE_URL.format(
            vin=self.vin,
            view=direction.value,
        )
        # the accept field of the header needs to be updated as we want a png not the usual JSON
        async with MyBMWClient(self.account.mybmw_client_config, brand=self.brand) as client:
            response = await client.get(url, headers={"accept": "image/png"})
        return response.content

    def __getattr__(self, item):
        """In the first version: just get the attributes from the dict.

        In a later version we might parse the attributes to provide a more advanced API.
        :param item: item to get, as defined in VEHICLE attributes
        """
        if item in get_class_property_names(self):
            return getattr(self, item)
        if item in get_class_property_names(self.status):
            return getattr(self.status, item)
        return self.attributes.get(item)

    def as_dict(self) -> dict:
        """Return all attributes and parameters, without `self.remote_services`."""
        return serialize_for_json(self, ["remote_services"])
