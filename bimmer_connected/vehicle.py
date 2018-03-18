"""Models state and remote services of one vehicle."""
from enum import Enum
import logging

from bimmer_connected.state import VehicleState
from bimmer_connected.remote_services import RemoteServices

_LOGGER = logging.getLogger(__name__)


class DriveTrainType(Enum):
    """Different types of drive trains."""
    CONVENTIONAL = 'CONV'
    PHEV = 'PHEV'
    BEV = 'BEV'
    BEV_REX = 'BEV_REX'


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
    def name(self):
        """Get the name of the vehicle."""
        return self.attributes['model']

    def __getattr__(self, item):
        """In the first version: just get the attributes from the dict.

        In a later version we might parse the attributes to provide a more advanced API.
        :param item: item to get, as defined in VEHICLE_ATTRIBUTES
        """
        return self.attributes.get(item)

    def __str__(self):
        """Use the name as identifier for the vehicle."""
        return '{}: {}'.format(self.__class__, self.name)
