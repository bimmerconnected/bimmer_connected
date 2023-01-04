"""Models state and remote services of one vehicle."""
import datetime
import logging
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Type

from bimmer_connected.api.client import MyBMWClient
from bimmer_connected.const import ATTR_ATTRIBUTES, ATTR_CAPABILITIES, ATTR_STATE, VEHICLE_IMAGE_URL, CarBrands
from bimmer_connected.models import StrEnum, ValueWithUnit
from bimmer_connected.utils import deprecated, parse_datetime
from bimmer_connected.vehicle.charging_profile import ChargingProfile
from bimmer_connected.vehicle.const import COMBUSTION_ENGINE_DRIVE_TRAINS, HV_BATTERY_DRIVE_TRAINS, DriveTrainType
from bimmer_connected.vehicle.doors_windows import DoorsAndWindows
from bimmer_connected.vehicle.fuel_and_battery import FuelAndBattery
from bimmer_connected.vehicle.location import VehicleLocation
from bimmer_connected.vehicle.remote_services import RemoteServices
from bimmer_connected.vehicle.reports import CheckControlMessageReport, ConditionBasedServiceReport
from bimmer_connected.vehicle.vehicle_status import VehicleStatus

if TYPE_CHECKING:
    from bimmer_connected.account import MyBMWAccount
    from bimmer_connected.models import VehicleDataBase


_LOGGER = logging.getLogger(__name__)


class VehicleViewDirection(StrEnum):
    """Viewing angles for the vehicle.

    This is used to get a rendered image of the vehicle.
    """

    FRONTSIDE = "VehicleStatus"  # also available as AngleSideViewForty
    FRONT = "FrontView"
    # REARSIDE = 'REARSIDE'
    # REAR = 'REAR'
    SIDE = "SideViewLeft"
    # DASHBOARD = 'DASHBOARD'
    # DRIVERDOOR = 'DRIVERDOOR'
    # REARBIRDSEYE = 'REARBIRDSEYE'
    UNKNOWN = "UNKNOWN"


class LscType(StrEnum):
    """Known Values for lsc_type field.

    Not really sure, what this value really contains.
    """

    NOT_CAPABLE = "NOT_CAPABLE"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    ACTIVATED = "ACTIVATED"
    UNKNOWN = "UNKNOWN"


# pylint: disable=too-many-public-methods,too-many-instance-attributes
class MyBMWVehicle:
    """Models state and remote services of one vehicle.

    :param account: MyBMW account this vehicle belongs to
    :param attributes: attributes of the vehicle as provided by the server
    """

    def __init__(
        self,
        account: "MyBMWAccount",
        vehicle_base: dict,
        vehicle_state: dict,
        fetched_at: Optional[datetime.datetime] = None,
    ) -> None:
        """Initializes a MyBMWVehicle."""
        self.account = account
        self.data = self.combine_data(account, vehicle_base, vehicle_state, fetched_at)
        self.status = VehicleStatus(self)
        self.remote_services = RemoteServices(self)
        self.fuel_and_battery: FuelAndBattery = FuelAndBattery(account_timezone=account.timezone)
        self.vehicle_location: VehicleLocation = VehicleLocation(account_region=account.region)
        self.doors_and_windows: DoorsAndWindows = DoorsAndWindows()
        self.condition_based_services: ConditionBasedServiceReport = ConditionBasedServiceReport()
        self.check_control_messages: CheckControlMessageReport = CheckControlMessageReport()
        self.charging_profile: Optional[ChargingProfile] = None

        self.update_state(vehicle_base, vehicle_state, fetched_at)

    def update_state(
        self, vehicle_base: dict, vehicle_state: dict, fetched_at: Optional[datetime.datetime] = None
    ) -> None:
        """Update the state of a vehicle."""
        vehicle_data = self.combine_data(self.account, vehicle_base, vehicle_state or {}, fetched_at)
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

    @staticmethod
    def combine_data(
        account: "MyBMWAccount", vehicle_base: dict, vehicle_state: dict, fetched_at: Optional[datetime.datetime] = None
    ) -> Dict:
        """Combine API responses and additional information to a single dictionary."""
        return {
            **vehicle_base,
            **vehicle_state,
            "is_metric": account.config.use_metric_units,
            "fetched_at": fetched_at or datetime.datetime.now(datetime.timezone.utc),
        }

    # # # # # # # # # # # # # # #
    # Generic attributes
    # # # # # # # # # # # # # # #

    @property
    def brand(self) -> CarBrands:
        """Get the car brand."""
        return CarBrands(self.data[ATTR_ATTRIBUTES]["brand"])

    @property
    def name(self) -> str:
        """Get the name of the vehicle."""
        return self.data[ATTR_ATTRIBUTES]["model"]

    @property
    def vin(self) -> str:
        """Get the VIN (vehicle identification number) of the vehicle."""
        return self.data["vin"]

    @property
    def drive_train(self) -> DriveTrainType:
        """Get the type of drive train of the vehicle."""
        return DriveTrainType(self.data[ATTR_ATTRIBUTES]["driveTrain"])

    @property
    def mileage(self) -> ValueWithUnit:
        """Get the mileage of the vehicle."""
        return ValueWithUnit(self.data[ATTR_STATE].get("currentMileage", 0), "km" if self.data["is_metric"] else "mi")

    @property
    def timestamp(self) -> Optional[datetime.datetime]:
        """Get the timestamp when the data was recorded."""
        timestamps = [
            ts
            for ts in [
                parse_datetime(str(self.data[ATTR_ATTRIBUTES].get("lastFetched"))),
                parse_datetime(str(self.data[ATTR_STATE].get("lastFetched"))),
            ]
            if ts
        ]
        if len(timestamps) == 0:
            return None
        return max(timestamps)

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
    def has_combustion_drivetrain(self) -> bool:
        """Return True if vehicle is equipped with an internal combustion engine.

        In this case we can get the state of the gas tank."""
        return self.drive_train in COMBUSTION_ENGINE_DRIVE_TRAINS

    @property
    def is_charging_plan_supported(self) -> bool:
        """Return True if charging control (weekly planner) is available."""
        return self.data[ATTR_CAPABILITIES].get("isChargingPlanSupported", False)

    @property
    def is_vehicle_tracking_enabled(self) -> bool:
        """Return True if vehicle finder is enabled in vehicle."""
        return self.data[ATTR_CAPABILITIES].get("vehicleFinder", False)

    @property
    def is_vehicle_active(self) -> bool:
        """Check if the vehicle is active/moving.

        If the vehicle was active/moving at the time of the last status update, current position is not available.
        """
        return False

    @property
    def lsc_type(self) -> LscType:
        """Get the lscType of the vehicle.

        Not really sure what that value really means. If it is NOT_CAPABLE, that probably means that the
        vehicle state will not contain much data.
        """
        return LscType(self.data[ATTR_CAPABILITIES].get("lastStateCallState", "NOT_CAPABLE"))

    @property
    def is_lsc_enabled(self) -> bool:
        """Return True if LastStateCall is enabled (vehicle automatically updates API)."""
        return self.data[ATTR_STATE]["isLscSupported"]

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
                "charging_end_time",
                "charging_time_label",
                "charging_status",
                "connection_status",
                "remaining_battery_percent",
                "remaining_range_electric",
                "last_charging_end_result",
            ]
        if self.has_combustion_drivetrain:
            result += ["remaining_fuel", "remaining_range_fuel", "remaining_fuel_percent"]
        return result

    @property
    def available_attributes(self) -> List[str]:
        """Get the list of non-drivetrain attributes available for this vehicle."""
        # attributes available in all vehicles
        result = ["gps_position", "vin"]
        if self.is_lsc_enabled:
            # generic attributes if lsc_type =! NOT_SUPPORTED
            result += self.drive_train_attributes
            result += [
                "condition_based_services",
                "check_control_messages",
                "door_lock_state",
                "timestamp",
            ]
            # required for existing Home Assistant binary sensors
            result += ["lids", "windows"]
        return result

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
        async with MyBMWClient(self.account.config, brand=self.brand) as client:
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
    @deprecated()
    def has_range_extender(self) -> bool:
        # pylint:disable=missing-function-docstring
        return False

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

    def __init__(self, account: "MyBMWAccount", vehicle_dict: dict) -> None:
        """Initializes a ConnectedDriveVehicle (deprecated)."""
        super().__init__(account, vehicle_dict, {})

    def update_state(
        self, vehicle_base: dict, vehicle_state: Optional[dict] = None, fetched_at: Optional[datetime.datetime] = None
    ) -> None:
        """Update the state of a vehicle."""

        super().update_state(vehicle_base, vehicle_state or {}, fetched_at)
