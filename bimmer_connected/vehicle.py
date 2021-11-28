"""Models state and remote services of one vehicle."""
from enum import Enum
import logging
from typing import TYPE_CHECKING, List

from bimmer_connected.charging_profile import ChargingProfile
from bimmer_connected.vehicle_status import VehicleStatus
from bimmer_connected.remote_services import RemoteServices
from bimmer_connected.const import SERVICE_PROPERTIES, SERVICE_STATUS, VEHICLE_IMAGE_URL
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


class CarBrand(str, Enum):
    """Car brands supported by the My BMW API."""
    @classmethod
    def _missing_(cls, value):
        for member in cls:
            if member.value == value.lower():
                return member
        raise ValueError("'{}' is not a valid {}".format(value, cls.__name__))

    BMW = "bmw"
    MINI = "mini"


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
        self.status = VehicleStatus()
        self.remote_services = RemoteServices(self._account, self)
        self.observer_latitude = None  # type: float
        self.observer_longitude = None  # type: float

        self.update_state(vehicle_dict)

    def update_state(self, vehicle_dict) -> None:
        """Update the state of a vehicle."""
        self.attributes = {k: v for k, v in vehicle_dict.items() if k not in [SERVICE_STATUS, SERVICE_PROPERTIES]}
        self.status.update_state({k: v for k, v in vehicle_dict.items() if k in [SERVICE_STATUS, SERVICE_PROPERTIES]})

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
    def brand(self) -> CarBrand:
        """Get the car brand."""
        return CarBrand(self.attributes["brand"])

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
    def drive_train_attributes(self) -> List[str]:
        """Get list of attributes available for the drive train of the vehicle.

        The list of available attributes depends if on the type of drive train.
        Some attributes only exist for electric/hybrid vehicles, others only if you
        have a combustion engine. Depending on the state of the vehicle, some of
        the attributes might still be None.
        """
        result = ['remaining_range_total', 'mileage']
        if self.has_hv_battery:
            result += ['charging_time_remaining', 'charging_status', 'charging_level_hv',
                       'connection_status', 'remaining_range_electric', 'last_charging_end_result']
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

    def get_vehicle_image(self, direction: VehicleViewDirection) -> bytes:
        """Get a rendered image of the vehicle.

        :returns bytes containing the image in PNG format.
        """
        url = VEHICLE_IMAGE_URL.format(
            vin=self.vin,
            server=self._account.server_url,
            view=direction.value,
        )
        header = self._account.request_header()
        # the accept field of the header needs to be updated as we want a png not the usual JSON
        header['accept'] = 'image/png'
        response = self._account.send_request(url, headers=header)
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

    def __str__(self) -> str:
        """Use the name as identifier for the vehicle."""
        return '{}: {}'.format(self.__class__, self.name)

    @property
    def to_json(self) -> dict:
        return serialize_for_json(self, ["_account", "remote_services"])

    def set_observer_position(self, latitude: float, longitude: float) -> None:
        """Set the position of the observer, who requests the vehicle state.

        Some vehicle require you to send your position to the server before you get the vehicle state.
        Your position must be within some range (2km?) of the vehicle to get you a proper answer.
        """
        if latitude is None or longitude is None:
            raise ValueError('Either latitude and longitude are both not None or both are None.')
        self.observer_latitude = latitude
        self.observer_longitude = longitude
