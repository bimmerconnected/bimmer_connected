"""Models state and remote services of one vehicle."""
from enum import Enum

from bimmer_connected.state import VehicleState
from bimmer_connected.remote_services import RemoteServices

#: List of known attributes of a vehicle
VEHICLE_ATTRIBUTES = [
    'series', 'vin', 'basicType', 'brand', 'hasRex', 'doorCount', 'steering', 'hasSunRoof',
    'bodyType', 'dcOnly', 'driveTrain', 'hasNavi', 'modelName']

#: List of known attributes of a vehicle spec
VEHICLE_SPEC_ATTRIBUTES = [
    "TANK_CAPACITY", "PERFORMANCE_TOP_SPEED", "PERFORMANCE_ACCELERATION", "WEIGHT_UNLADEN",
    "WEIGHT_MAX", "WEIGHT_PERMITTED_LOAD", "WEIGHT_PERMITTED_LOAD_FRONT", "WEIGHT_PERMITTED_LOAD_REAR",
    "ENGINE_CYLINDERS", "ENGINE_VALVES", "ENGINE_STROKE", "ENGINE_BORE", "ENGINE_OUTPUT_MAX_KW",
    "ENGINE_OUTPUT_MAX_HP", "ENGINE_SPEED_OUTPUT_MAX", "ENGINE_TORQUE_MAX",
    "ENGINE_SPEED_TORQUE_MAX", "ENGINE_COMPRESSION",
]

VEHICLE_SPECS_URL = '{server}/api/vehicle/specs/v1/{vin}'


class DriveTrainType(Enum):
    """Different types of drive trains."""
    CONVENTIONAL = 'CONV'


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
        self.specs = VehicleSpecs(account, self)

    def update_state(self) -> None:
        """Update the state of a vehicle."""
        self.state.update_data()
        self.specs.update_data()

    @property
    def has_rex(self) -> bool:
        """Check if the vehicle has a range extender."""
        return self.attributes['hasRex'] == '1'

    @property
    def drive_train(self) -> DriveTrainType:
        """Get the type of drive train of the vehicle."""
        return DriveTrainType(self.attributes['driveTrain'])

    def __getattr__(self, item):
        """In the first version: just get the attributes from the dict.

        In a later version we might parse the attributes to provide a more advanced API.
        :param item: item to get, as defined in VEHICLE_ATTRIBUTES
        """
        return self.attributes[item]


class VehicleSpecs(object):  # pylint: disable=too-few-public-methods
    """Get the specifications of the vehicle.

    :param account: account the vehicle belongs to
    :param vehicle: vehicle the specs belong to
    """

    def __init__(self, account, vehicle):
        self._account = account
        self._vehicle = vehicle
        self.attributes = None

    def update_data(self):
        """Fetch the specification from the server."""
        url = VEHICLE_SPECS_URL.format(server=self._account.server_url, vin=self._vehicle.vin)

        response = self._account.send_request(url)

        self.attributes = dict()
        for attribute in response.json():
            self.attributes[attribute['key']] = attribute['value']

    def __getattr__(self, item):
        """In the first version: just get the attributes from the dict.

        In a later version we might parse the attributes to provide a more advanced API.
        """
        if self.attributes is None:
            self.update_data()
        return self.attributes[item]
