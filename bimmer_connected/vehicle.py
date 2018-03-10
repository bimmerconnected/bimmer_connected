"""Models state and remote services of one vehicle."""
from enum import Enum
import logging

from bimmer_connected.state import VehicleState
from bimmer_connected.remote_services import RemoteServices
from bimmer_connected.const import VEHICLE_VIN_URL

_LOGGER = logging.getLogger(__name__)


#: List of known attributes of a vehicle
VEHICLE_ATTRIBUTES = [
    'series', 'vin', 'basicType', 'brand', 'hasRex', 'doorCount', 'steering', 'hasSunRoof',
    'bodyType', 'dcOnly', 'driveTrain', 'hasNavi', 'modelName']

class DriveTrainType(Enum):
    """Different types of drive trains."""
    CONVENTIONAL = 'CONV'
    PHEV = 'PHEV'
    BEV = 'BEV'
    BEV_REX = 'BEV_REX'


class ConnectedDriveVehicle(object):  # pylint: disable=too-few-public-methods
    """Models state and remote services of one vehicle.

    :param account: ConnectedDrive account this vehicle belongs to
    :param attributes: attributes of the vehicle as provided by the server
    """

    def __init__(self, account, attributes: dict) -> None:
        self._account = account
        self.attributes = attributes
        self.state = VehicleState(account, self)
        self.remote_services = RemoteServices(account, self)
        self._update_data()

    def update_state(self) -> None:
        """Update the state of a vehicle."""
        self.state.update_data()

    def _update_data(self):
        url = VEHICLE_VIN_URL.format(server=self._account.server_url, vin=self.vin)

        response = self._account.send_request(url)
        self.attributes.update(response.json()['vehicle'])

    @property
    def has_rex(self) -> bool:
        """Check if the vehicle has a range extender."""
        return self.attributes['hasRex'] == '1'

    @property
    def drive_train(self) -> DriveTrainType:
        """Get the type of drive train of the vehicle."""
        return DriveTrainType(self.attributes['driveTrain'])

    @property
    def name(self):
        """Get the name of the vehicle."""
        return self.attributes['modelName']

    def __getattr__(self, item):
        """In the first version: just get the attributes from the dict.

        In a later version we might parse the attributes to provide a more advanced API.
        :param item: item to get, as defined in VEHICLE_ATTRIBUTES
        """
        return self.attributes[item]

