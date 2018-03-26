"""Models state and remote services of one vehicle."""
from enum import Enum
import logging
from typing import List

from bimmer_connected.state import VehicleState
from bimmer_connected.remote_services import RemoteServices
from bimmer_connected.const import VEHICLE_IMAGE_URL

_LOGGER = logging.getLogger(__name__)


class DriveTrainType(Enum):
    """Different types of drive trains."""
    CONVENTIONAL = 'CONV'
    PHEV = 'PHEV'
    BEV = 'BEV'
    BEV_REX = 'BEV_REX'


#: Set of drive trains that have a combustion engine
COMBUSTION_ENGINE_DRIVE_TRAINS = {DriveTrainType.CONVENTIONAL, DriveTrainType.PHEV, DriveTrainType.BEV_REX}

#: set of drive trains that have a high voltage battery
HV_BATTERY_DRIVE_TRAINS = {DriveTrainType.PHEV, DriveTrainType.BEV, DriveTrainType.BEV_REX}


class VehicleViewDirection(Enum):
    """Viewing angles for the vehicle.

    This is used to get a rendered image of the vehicle.
    """
    FRONTSIDE = 'FRONTSIDE'
    FRONT = 'FRONT'
    REARSIDE = 'REARSIDE'
    REAR = 'REAR'
    SIDE = 'SIDE'
    DASHBOARD = 'DASHBOARD'
    DRIVERDOOR = 'DRIVERDOOR'
    REARBIRDSEYE = 'REARBIRDSEYE'


class ConnectedDriveVehicle(object):
    """Models state and remote services of one vehicle.

    :param account: ConnectedDrive account this vehicle belongs to
    :param attributes: attributes of the vehicle as provided by the server
    """

    def __init__(self, account, attributes: dict) -> None:
        self._account = account
        self.attributes = attributes
        self.state = VehicleState(account, self)
        self.remote_services = RemoteServices(account, self)

    def update_state(self) -> None:
        """Update the state of a vehicle."""
        self.state.update_data()

    @property
    def drive_train(self) -> DriveTrainType:
        """Get the type of drive train of the vehicle."""
        return DriveTrainType(self.attributes['driveTrain'])

    @property
    def name(self) -> str:
        """Get the name of the vehicle."""
        return self.attributes['model']

    @property
    def has_hv_battery(self) -> bool:
        """Return True if vehicle is equipped with a high voltage battery.

        In this case we can get the state of the battery in the state attributes.
        """
        return self.drive_train in HV_BATTERY_DRIVE_TRAINS

    @property
    def has_internal_combustion_engine(self) -> bool:
        """Return True if vehicle is equipped with an internal combustion engine.

        In this case we can get the state of the gas tank."""
        return self.drive_train in COMBUSTION_ENGINE_DRIVE_TRAINS

    @property
    def drive_train_attributes(self) -> List[str]:
        """Get list of attributes available for the drive train of the vehicle.

        The list of available attributes depends if on the type of drive train.
        Some attributes only exist for electric/hybrid vehicles, others only if you
        have a combustion engine. Depending on the state of the vehicle, some of
        the attributes might still be None.
        """
        result = ['remaining_range_total']
        if self.has_hv_battery:
            result += ['charging_time_remaining', 'charging_status', 'max_range_electric', 'charging_level_hv']
        if self.has_internal_combustion_engine:
            result += ['remaining_fuel']
        if self.has_hv_battery and self.has_internal_combustion_engine:
            result += ['remaining_range_electric', 'remaining_range_fuel']
        return result

    def get_vehicle_image(self, width: int, height: int, direction: VehicleViewDirection) -> bytes:
        """Get a rendered image of the vehicle.

        :returns bytes containing the image in PNG format.
        """
        url = VEHICLE_IMAGE_URL.format(
            vin=self.vin,
            server=self._account.server_url,
            width=width,
            height=height,
            view=direction.value,
        )
        header = self._account.request_header
        # the accept field of the header needs to be updated as we want a png not the usual JSON
        header['accept'] = 'image/png'
        response = self._account.send_request(url, headers=header)
        return response.content

    def __getattr__(self, item):
        """In the first version: just get the attributes from the dict.

        In a later version we might parse the attributes to provide a more advanced API.
        :param item: item to get, as defined in VEHICLE_ATTRIBUTES
        """
        return self.attributes.get(item)

    def __str__(self) -> str:
        """Use the name as identifier for the vehicle."""
        return '{}: {}'.format(self.__class__, self.name)
