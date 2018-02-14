"""Models state and remote services of one vehicle."""

from bimmer_connected.state import VehicleState
from bimmer_connected.remote_services import RemoteServices

# List of known attributes of a vehicle
ATTRIBUTES = ['series', 'vin', 'basicType', 'brand', 'hasRex', 'doorCount', 'steering', 'hasSunRoof', 'bodyType',
              'dcOnly', 'driveTrain', 'hasNavi', 'modelName']


class ConnectedDriveVehicle(object):  # pylint: disable=too-few-public-methods
    """Models state and remote services of one vehicle."""

    def __init__(self, account, attributes: dict) -> None:
        """Constructor."""
        self._account = account
        self.attributes = attributes
        self.state = VehicleState(account, self)
        self.remote_services = RemoteServices(account, self)

    def update_state(self):
        """Update the state of a vehicle."""
        self.state.update_data()

    def __getattr__(self, item):
        """In the first version: just get the attributes from the dict.

        In a later version we might parse the attributes to provide a more advanced API.
        """
        return self.attributes[item]
