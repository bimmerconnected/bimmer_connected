"""Models state and remote services of one vehicle."""
import datetime
import logging
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Type

from bimmer_connected.api.client import MyBMWClient
from bimmer_connected.const import SERVICE_PROPERTIES, SERVICE_STATUS, VEHICLE_IMAGE_URL, CarBrands
from bimmer_connected.utils import deprecated, parse_datetime
from bimmer_connected.vehicle.charging_profile import ChargingProfile
from bimmer_connected.vehicle.doors_windows import DoorsAndWindows
from bimmer_connected.vehicle.fuel_and_battery import FuelAndBattery
from bimmer_connected.vehicle.location import VehicleLocation
from bimmer_connected.vehicle.models import StrEnum, ValueWithUnit
from bimmer_connected.vehicle.remote_services import RemoteServices
from bimmer_connected.vehicle.reports import CheckControlMessageReport, ConditionBasedServiceReport
from bimmer_connected.vehicle.vehicle_status import VehicleStatus

if TYPE_CHECKING:
    from bimmer_connected.account import MyBMWAccount
    from bimmer_connected.vehicle.models import VehicleDataBase


_LOGGER = logging.getLogger(__name__)


class DriveTrainType(StrEnum):
    """Different types of drive trains."""

    COMBUSTION = "COMBUSTION"
    PLUGIN_HYBRID = "PLUGIN_HYBRID"  # PHEV
    ELECTRIC = "ELECTRIC"
    HYBRID = "HYBRID"  # mild hybrids


#: Set of drive trains that have a combustion engine
COMBUSTION_ENGINE_DRIVE_TRAINS = {DriveTrainType.COMBUSTION, DriveTrainType.PLUGIN_HYBRID}

#: set of drive trains that have a high voltage battery
HV_BATTERY_DRIVE_TRAINS = {DriveTrainType.PLUGIN_HYBRID, DriveTrainType.ELECTRIC}


class VehicleViewDirection(StrEnum):
    """Viewing angles for the vehicle.

    This is used to get a rendered image of the vehicle.
    """

    FRONTSIDE = "VehicleStatus"
    FRONT = "VehicleInfo"
    # REARSIDE = 'REARSIDE'
    # REAR = 'REAR'
    SIDE = "ChargingHistory"
    # DASHBOARD = 'DASHBOARD'
    # DRIVERDOOR = 'DRIVERDOOR'
    # REARBIRDSEYE = 'REARBIRDSEYE'


class LscType(StrEnum):
    """Known Values for lsc_type field.

    Not really sure, what this value really contains.
    """

    NOT_CAPABLE = "NOT_CAPABLE"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    ACTIVATED = "ACTIVATED"


# pylint: disable=too-many-public-methods,too-many-instance-attributes
class MyBMWVehicle:
    """Models state and remote services of one vehicle.

    :param account: MyBMW account this vehicle belongs to
    :param attributes: attributes of the vehicle as provided by the server
    """

    def __init__(self, account: "MyBMWAccount", vehicle_data: dict) -> None:
        """Initializes a MyBMWVehicle."""
        self.account = account
        self.data = vehicle_data
        self.status = VehicleStatus(self)
        self.remote_services = RemoteServices(self)
        self.fuel_and_battery: FuelAndBattery = FuelAndBattery(account_timezone=account.timezone)
        self.vehicle_location: VehicleLocation = VehicleLocation(account_region=account.region)
        self.doors_and_windows: DoorsAndWindows = DoorsAndWindows()
        self.condition_based_services: ConditionBasedServiceReport = ConditionBasedServiceReport()
        self.check_control_messages: CheckControlMessageReport = CheckControlMessageReport()
        self.charging_profile: Optional[ChargingProfile] = None

        self.update_state(vehicle_data)

    def update_state(self, vehicle_data) -> None:
        """Update the state of a vehicle."""
        self.data = vehicle_data

        update_entities: List[Tuple[Type["VehicleDataBase"], str]] = [
            (FuelAndBattery, "fuel_and_battery"),
            (VehicleLocation, "vehicle_location"),
            (DoorsAndWindows, "doors_and_windows"),
            (ConditionBasedServiceReport, "condition_based_services"),
            (CheckControlMessageReport, "check_control_messages"),
            (ChargingProfile, "charging_profile"),
        ]
        for cls, vehicle_attribute in update_entities:
            if getattr(self, vehicle_attribute) is None:
                setattr(self, vehicle_attribute, cls.from_vehicle_data(vehicle_data))
            else:
                curr_attr: "VehicleDataBase" = getattr(self, vehicle_attribute)
                curr_attr.update_from_vehicle_data(vehicle_data)

    # # # # # # # # # # # # # # #
    # Generic attributes
    # # # # # # # # # # # # # # #

    @property
    def _status(self) -> Dict:
        """A shortcut to `data.status`."""
        return self.data[SERVICE_STATUS]

    @property
    def _properties(self) -> Dict:
        """A shortcut to `data.properties`."""
        return self.data[SERVICE_PROPERTIES]

    @property
    def brand(self) -> CarBrands:
        """Get the car brand."""
        return CarBrands(self.data["brand"])

    @property
    def name(self) -> str:
        """Get the name of the vehicle."""
        return self.data["model"]

    @property
    def vin(self) -> str:
        """Get the VIN (vehicle identification number) of the vehicle."""
        return self.data["vin"]

    @property
    def drive_train(self) -> DriveTrainType:
        """Get the type of drive train of the vehicle."""
        return DriveTrainType(self.data["driveTrain"])

    @property
    def mileage(self) -> ValueWithUnit:
        """Get the mileage of the vehicle."""
        return ValueWithUnit(self._status["currentMileage"]["mileage"], self._status["currentMileage"]["units"])

    @property
    def timestamp(self) -> Optional[datetime.datetime]:
        """Get the timestamp when the data was recorded."""
        timestamps = [
            ts
            for ts in [
                parse_datetime(str(self._properties.get("lastUpdatedAt"))),
                parse_datetime(str(self._status.get("lastUpdatedAt"))),
            ]
            if ts
        ]
        if len(timestamps) == 0:
            return None
        return max(timestamps)

    @property
    def last_update_reason(self) -> str:
        """The reason for the last state update."""
        return self._status["timestampMessage"]

    # # # # # # # # # # # # # # #
    # Capabilities & properties
    # # # # # # # # # # # # # # #

    @property
    def has_electric_drivetrain(self) -> bool:
        """Return True if vehicle is equipped with a high voltage battery.

        In this case we can get the state of the battery in the state attributes.
        """
        return self.drive_train in HV_BATTERY_DRIVE_TRAINS

    @property
    def has_range_extender_drivetrain(self) -> bool:
        """Return True if vehicle is equipped with a range extender.

        In this case we can get the state of the gas tank."""
        return self.drive_train == DriveTrainType.ELECTRIC and self.fuel_indicator_count == 3

    @property
    def has_combustion_drivetrain(self) -> bool:
        """Return True if vehicle is equipped with an internal combustion engine.

        In this case we can get the state of the gas tank."""
        return self.drive_train in COMBUSTION_ENGINE_DRIVE_TRAINS

    @property
    def is_charging_plan_supported(self) -> bool:
        """Return True if charging control (weekly planner) is available."""
        return self.data["capabilities"]["isChargingPlanSupported"]

    @property
    def is_vehicle_tracking_enabled(self) -> bool:
        """Return True if vehicle finder is enabled in vehicle."""
        return self.data["capabilities"]["vehicleFinder"]["isEnabled"]

    @property
    def is_vehicle_active(self) -> bool:
        """Check if the vehicle is active/moving.

        If the vehicle was active/moving at the time of the last status update, current position is not available.
        """
        return self._properties["inMotion"]

    @property
    def is_lsc_enabled(self) -> bool:
        """Return True if LastStateCall is enabled (vehicle automatically updates API)."""
        return self.data["capabilities"]["lastStateCall"]["lscState"] == "ACTIVATED"

    @property
    def drive_train_attributes(self) -> List[str]:
        """Get list of attributes available for the drive train of the vehicle.

        The list of available attributes depends if on the type of drive train.
        Some attributes only exist for electric/hybrid vehicles, others only if you
        have a combustion engine. Depending on the state of the vehicle, some of
        the attributes might still be None.
        """
        result = ["remaining_range_total", "mileage"]
        if self.has_electric_drivetrain:
            result += [
                "charging_time_remaining",
                "charging_start_time",
                "charging_end_time",
                "charging_time_label",
                "charging_status",
                "connection_status",
                "remaining_battery_percent",
                "remaining_range_electric",
                "last_charging_end_result",
            ]
        if self.has_combustion_drivetrain or self.has_range_extender_drivetrain:
            result += ["remaining_fuel", "remaining_range_fuel", "remaining_fuel_percent"]
        return result

    @property
    def lsc_type(self) -> LscType:
        """Get the lscType of the vehicle.

        Not really sure what that value really means. If it is NOT_CAPABLE, that probably means that the
        vehicle state will not contain much data.
        """
        return LscType(self.data["capabilities"]["lastStateCall"].get("lscState"))

    @property
    def available_attributes(self) -> List[str]:
        """Get the list of non-drivetrain attributes available for this vehicle."""
        # attributes available in all vehicles
        result = ["gps_position", "vin"]
        if self.lsc_type == LscType.ACTIVATED:
            # generic attributes if lsc_type =! NOT_SUPPORTED
            result += self.drive_train_attributes
            result += [
                "condition_based_services",
                "check_control_messages",
                "door_lock_state",
                "timestamp",
                "last_update_reason",
            ]
            # required for existing Home Assistant binary sensors
            result += ["lids", "windows", "convertible_top"]
        return result

    @property
    def fuel_indicator_count(self) -> int:
        """Gets the number of fuel indicators.

        Can be used to identify REX vehicles if driveTrain == ELECTRIC.
        """
        return len(self._status["fuelIndicators"])

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

    # # # # # # # # # # # # # # #
    # Deprecated
    # # # # # # # # # # # # # # #

    @property  # type: ignore[misc]
    @deprecated("vehicle.has_electric_drivetrain")
    def has_hv_battery(self) -> bool:
        # pylint:disable=missing-function-docstring
        return self.has_electric_drivetrain

    @property  # type: ignore[misc]
    @deprecated("vehicle.has_range_extender_drivetrain")
    def has_range_extender(self) -> bool:
        # pylint:disable=missing-function-docstring
        return self.has_range_extender_drivetrain

    @property  # type: ignore[misc]
    @deprecated("vehicle.has_combustion_drivetrain")
    def has_internal_combustion_engine(self) -> bool:
        # pylint:disable=missing-function-docstring
        return self.has_combustion_drivetrain

    @property  # type: ignore[misc]
    @deprecated("vehicle.is_charging_plan_supported")
    def has_weekly_planner_service(self) -> bool:
        # pylint:disable=missing-function-docstring
        return self.is_charging_plan_supported


@deprecated("MyBMWVehicle")
class ConnectedDriveVehicle(MyBMWVehicle):
    """Deprecated class name for compatibility."""
