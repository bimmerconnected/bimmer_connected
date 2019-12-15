"""Models state and remote services of one vehicle."""
from enum import Enum
import logging
from typing import List
import json
from urllib.parse import urlencode

from bimmer_connected.state import VehicleState, WINDOWS, LIDS
from bimmer_connected.remote_services import RemoteServices
from bimmer_connected.const import VEHICLE_IMAGE_URL, VEHICLE_POI_URL

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


class LscType(Enum):
    """Known Values for lsc_type field.

    Not really sure, what this value really contains.
    """
    NOT_SUPPORTED = 'NOT_SUPPORTED'
    LSC_BASIS = 'LSC_BASIS'
    I_LSC_IMM = 'I_LSC_IMM'
    UNKNOWN = 'UNKNOWN'
    LSC_PHEV = 'LSC_PHEV'


# pylint: disable=too-many-instance-attributes, too-few-public-methods
class PointOfInterest:
    """Point of interest to be sent to the vehicle.

    The latitude/longitude of a POI are mandatory, all other attributes are optional. CamelCase attribute names are
    used here so that we do not have to convert the names between the attributes and the keys as expected on the server.
    """

    # pylint: disable=too-many-arguments
    def __init__(self, latitude: float, longitude: float, name: str = None,
                 additionalInfo: str = None, street: str = None, city: str = None,
                 postalCode: str = None, country: str = None, website: str = None,
                 phoneNumbers: [str] = None):
        """Constructor.

        :arg latitude: latitude of the POI
        :arg longitude: longitude of the POI
        :arg name: name of the POI (Optional)
        :arg additionalInfo: additional text shown below the address (Optional)
        :arg street: street with house number of the POI (Optional)
        :arg city: city of the POI (Optional)
        :arg postalCode: zip code of the POI (Optional)
        :arg country: country of the POI (Optional)
        :arg website: website of the POI (Optional)
        :arg phoneNumbers: List of phone numbers of the POI (Optional)
        """
        # pylint: disable=invalid-name
        self.lat = latitude  # type: float
        self.lon = longitude  # type: float
        self.name = name  # type: str
        self.additionalInfo = additionalInfo if additionalInfo is not None \
            else 'Sent with ♥ by bimmer_connected'  # type: str
        self.street = street  # type: str
        self.city = city  # type: str
        self.postalCode = postalCode  # type: str
        self.country = country  # type: str
        self.website = website  # type: str
        self.phoneNumbers = phoneNumbers  # type: List[str]


class Message:
    """Text message or PointOfInterst to be sent to the vehicle."""

    @classmethod
    def from_poi(cls, poi: PointOfInterest):
        """Create a message from a PointOfInterest"""
        return cls(poi.__dict__)

    @classmethod
    def from_text(cls, text: str, subject: str = None):
        """Create a text message"""
        return cls({"name": subject, "additionalInfo": text[:255]})

    def __init__(self, data: dict):
        self.data = data

    @property
    def as_server_request(self) -> str:
        """Convert to a dictionary so that it can be sent to the server."""
        result = {
            'poi': {k: v for k, v in self.data.items() if v is not None}
        }
        return urlencode({'data': json.dumps(result)})


class ConnectedDriveVehicle:
    """Models state and remote services of one vehicle.

    :param account: ConnectedDrive account this vehicle belongs to
    :param attributes: attributes of the vehicle as provided by the server
    """

    def __init__(self, account, attributes: dict) -> None:
        self._account = account
        self.attributes = attributes
        self.state = VehicleState(account, self)
        self.remote_services = RemoteServices(account, self)
        self.observer_latitude = 0.0  # type: float
        self.observer_longitude = 0.0  # type: float

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
        result = ['remaining_range_total', 'remaining_fuel', 'mileage']
        if self.has_hv_battery:
            result += ['charging_time_remaining', 'charging_status', 'max_range_electric', 'charging_level_hv',
                       'chargingConnectionType', 'chargingInductivePositioning', 'connectionStatus',
                       'lastChargingEndReason', 'remaining_range_electric', 'lastChargingEndResult']
        if self.has_internal_combustion_engine:
            result += ['remaining_range_fuel']
        if self.has_hv_battery and self.has_internal_combustion_engine:
            result += ['maxFuel']
        return result

    @property
    def lsc_type(self) -> LscType:
        """Get the lscType of the vehicle.

        Not really sure what that value really means. If it is NOT_SUPPORTED, that probably means that the
        vehicle state will not contain much data.
        """
        return LscType(self.attributes.get('lscType'))

    @property
    def available_attributes(self) -> List[str]:
        """Get the list of non-drivetrain attributes available for this vehicle."""
        # attributes available in all vehicles
        result = ['gps_position', 'steering', 'timestamp', 'vin']
        if self.lsc_type in [LscType.LSC_BASIS, LscType.I_LSC_IMM, LscType.LSC_PHEV]:
            # generic attributes if lsc_type =! NOT_SUPPORTED
            result += LIDS
            result += WINDOWS
            result += self.drive_train_attributes
            result += ['DCS_CCH_Activation', 'DCS_CCH_Ongoing', 'condition_based_services',
                       'check_control_messages', 'door_lock_state', 'internalDataTimeUTC',
                       'parking_lights', 'positionLight', 'last_update_reason', 'singleImmediateCharging']
            # required for existing Home Assistant binary sensors
            result += ['lights_parking', 'lids', 'windows']
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

    def set_observer_position(self, latitude: float, longitude: float) -> None:
        """Set the position of the observer, who requests the vehicle state.

        Some vehicle require you to send your position to the server before you get the vehicle state.
        Your position must be within some range (2km?) of the vehicle to get you a proper answer.
        """
        if (latitude == 0.0 or longitude == 0.0) and latitude != longitude:
            raise ValueError('Either latitude AND longitude are set or none of them. You cannot set only one of them!')
        self.observer_latitude = latitude
        self.observer_longitude = longitude

    def send_message(self, msg: Message) -> None:
        """Send a message/point of interest to the vehicle."""
        url = VEHICLE_POI_URL.format(
            vin=self.vin,
            server=self._account.server_url
        )
        header = self._account.request_header
        # the accept field of the header needs to be updated as we want a png not the usual JSON
        header['Content-Type'] = 'application/x-www-form-urlencoded'
        self._account.send_request(url, headers=header, data=msg.as_server_request, post=True, expected_response=204)
