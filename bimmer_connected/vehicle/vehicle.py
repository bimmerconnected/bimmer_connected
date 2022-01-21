"""Models state and remote services of one vehicle."""
from enum import Enum
import logging
from typing import TYPE_CHECKING, List

from bimmer_connected.vehicle.charging_profile import ChargingProfile
from bimmer_connected.api.client import MyBMWClient
from bimmer_connected.vehicle.vehicle_status import VehicleStatus
from bimmer_connected.vehicle.remote_services import RemoteServices
from bimmer_connected.const import SERVICE_PROPERTIES, SERVICE_STATUS, VEHICLE_IMAGE_URL, CarBrands
from bimmer_connected.utils import SerializableBaseClass, get_class_property_names, serialize_for_json

if TYPE_CHECKING:
    from bimmer_connected.account import ConnectedDriveAccount

_LOGGER = logging.getLogger(__name__)


class DriveTrainType(str, Enum):
    """Different types of drive trains."""
    COMBUSTION = 'COMBUSTION'
    PLUGIN_HYBRID = 'PLUGIN_HYBRID'  # PHEV
    ELECTRIC = 'ELECTRIC'
    HYBRID = 'HYBRID'  # mild hybrids


#: Set of drive trains that have a combustion engine
COMBUSTION_ENGINE_DRIVE_TRAINS = {DriveTrainType.COMBUSTION, DriveTrainType.PLUGIN_HYBRID}

#: set of drive trains that have a high voltage battery
HV_BATTERY_DRIVE_TRAINS = {DriveTrainType.PLUGIN_HYBRID, DriveTrainType.ELECTRIC}


class VehicleViewDirection(str, Enum):
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


class LscType(str, Enum):
    """Known Values for lsc_type field.

    Not really sure, what this value really contains.
    """
    NOT_CAPABLE = 'NOT_CAPABLE'
    NOT_SUPPORTED = 'NOT_SUPPORTED'
    ACTIVATED = 'ACTIVATED'


class ConnectedDriveVehicle(SerializableBaseClass):
    """Models state and remote services of one vehicle.

    :param account: ConnectedDrive account this vehicle belongs to
    :param attributes: attributes of the vehicle as provided by the server
    """

    def __init__(self, account: "ConnectedDriveAccount", vehicle_dict: dict) -> None:
        self._account = account
        self.attributes = None
        self.status = VehicleStatus(account)
        self.remote_services = RemoteServices(self)

        self.update_state(vehicle_dict)

    def update_state(self, vehicle_dict) -> None:
        """Update the state of a vehicle."""
        if SERVICE_STATUS in vehicle_dict and SERVICE_PROPERTIES in vehicle_dict:
            self.attributes = {k: v for k, v in vehicle_dict.items() if k not in [SERVICE_STATUS, SERVICE_PROPERTIES]}
            self.status.update_state(
                {
                    k: v
                    for k, v
                    in vehicle_dict.items()
                    if k in [SERVICE_STATUS, SERVICE_PROPERTIES]
                }
            )
        else:
            _LOGGER.warning("Incomplete vehicle status data: %s", vehicle_dict)

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

    async def get_vehicle_image(self, direction: VehicleViewDirection) -> bytes:
        """Get a rendered image of the vehicle.

        :returns bytes containing the image in PNG format.
        """
        url = VEHICLE_IMAGE_URL.format(
            vin=self.vin,
            view=direction.value,
        )
        # the accept field of the header needs to be updated as we want a png not the usual JSON
        async with MyBMWClient(self._account.mybmw_client_config, brand=self.brand) as client:
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