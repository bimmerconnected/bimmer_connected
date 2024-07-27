"""Generals models used for bimmer_connected."""

import datetime
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from bimmer_connected.const import ATTR_ATTRIBUTES, ATTR_STATE
from bimmer_connected.models import StrEnum, ValueWithUnit, VehicleDataBase
from bimmer_connected.utils import get_next_occurrence
from bimmer_connected.vehicle.const import COMBUSTION_ENGINE_DRIVE_TRAINS, HV_BATTERY_DRIVE_TRAINS, DriveTrainType

_LOGGER = logging.getLogger(__name__)


class ChargingState(StrEnum):
    """Charging state of electric vehicle."""

    DEFAULT = "DEFAULT"
    CHARGING = "CHARGING"
    ERROR = "ERROR"
    COMPLETE = "COMPLETE"
    FULLY_CHARGED = "FULLY_CHARGED"
    FINISHED_FULLY_CHARGED = "FINISHED_FULLY_CHARGED"
    FINISHED_NOT_FULL = "FINISHED_NOT_FULL"
    INVALID = "INVALID"
    NOT_CHARGING = "NOT_CHARGING"
    PLUGGED_IN = "PLUGGED_IN"
    WAITING_FOR_CHARGING = "WAITING_FOR_CHARGING"
    TARGET_REACHED = "TARGET_REACHED"
    UNKNOWN = "UNKNOWN"


@dataclass
class FuelAndBattery(VehicleDataBase):
    """Provides an accessible version of `status.FuelAndBattery`."""

    remaining_range_fuel: Optional[ValueWithUnit] = ValueWithUnit(None, None)
    """Get the remaining range of the vehicle on fuel."""

    remaining_range_electric: Optional[ValueWithUnit] = ValueWithUnit(None, None)
    """Get the remaining range of the vehicle on electricity."""

    remaining_range_total: Optional[ValueWithUnit] = ValueWithUnit(None, None)
    """Get the total remaining range of the vehicle (fuel + electricity, if available)."""

    remaining_fuel: Optional[ValueWithUnit] = ValueWithUnit(None, None)
    """Get the remaining fuel of the vehicle."""

    remaining_fuel_percent: Optional[int] = None
    """State of charge of the high voltage battery in percent."""

    remaining_battery_percent: Optional[int] = None
    """State of charge of the high voltage battery in percent."""

    charging_status: Optional[ChargingState] = None
    """Charging state of the vehicle."""

    charging_start_time: Optional[datetime.datetime] = None
    """The planned time the vehicle will start charging in local time."""

    charging_end_time: Optional[datetime.datetime] = None
    """The estimated time the vehicle will have finished charging."""

    is_charger_connected: bool = False
    """Get status of the connection"""

    charging_target: Optional[int] = None
    """State of charging target in percent."""

    @classmethod
    def from_vehicle_data(cls, vehicle_data: Dict):
        """Create the class based on vehicle data from API."""
        parsed = cls._parse_vehicle_data(vehicle_data) or {}
        if len(parsed) > 0:
            return cls(**parsed)
        return None

    @classmethod
    def _parse_vehicle_data(cls, vehicle_data: Dict) -> Optional[Dict]:
        """Parse fuel indicators based on Ids."""
        retval: Dict[str, Any] = {}
        drivetrain = DriveTrainType(vehicle_data.get(ATTR_ATTRIBUTES, {}).get("driveTrain") or DriveTrainType.UNKNOWN)

        # return early if state data hasn't been loaded or no combustion/electric data is available
        if (
            ATTR_STATE not in vehicle_data
            or len({"combustionFuelLevel", "electricChargingState"}.intersection(set(vehicle_data[ATTR_STATE]))) == 0
        ):
            return retval

        state = vehicle_data["state"]

        if drivetrain in COMBUSTION_ENGINE_DRIVE_TRAINS:
            retval.update(cls._parse_fuel_data(state.get("combustionFuelLevel", {})))

        if drivetrain in HV_BATTERY_DRIVE_TRAINS and (electric_data := state.get("electricChargingState", {})):
            retval.update(
                cls._parse_electric_data(
                    electric_data,
                    vehicle_data["fetched_at"],
                    state.get("chargingProfile", {}).get("reductionOfChargeCurrent"),
                ),
            )

        if drivetrain in set(COMBUSTION_ENGINE_DRIVE_TRAINS).intersection(HV_BATTERY_DRIVE_TRAINS):
            # for hybrid vehicles the remaining_range_fuel returned by the API seems to be the total remaining range
            # to calculate the correct remaining range on fuel, we have to subtract the remaining electric range
            # this does not seem to apply for the old I3 with range extender

            fuel: ValueWithUnit = retval.get("remaining_range_fuel", ValueWithUnit(None, None))
            electric: ValueWithUnit = retval.get("remaining_range_electric", ValueWithUnit(None, None))

            if drivetrain == DriveTrainType.ELECTRIC_WITH_RANGE_EXTENDER:
                retval["remaining_range_total"] = ValueWithUnit(
                    (fuel.value or 0) + (electric.value or 0),
                    fuel.unit or electric.unit,
                )
            else:
                retval["remaining_range_total"] = retval["remaining_range_fuel"]
                retval["remaining_range_fuel"] = ValueWithUnit(
                    (fuel.value or 0) - (electric.value or 0),
                    fuel.unit or electric.unit,
                )
        elif drivetrain in COMBUSTION_ENGINE_DRIVE_TRAINS and "remaining_range_fuel" in retval:
            retval["remaining_range_total"] = retval["remaining_range_fuel"]
        elif drivetrain in HV_BATTERY_DRIVE_TRAINS and "remaining_range_electric" in retval:
            retval["remaining_range_total"] = retval["remaining_range_electric"]

        return retval

    @staticmethod
    def _parse_fuel_data(fuel_data: Dict) -> Dict:
        """Parse fuel data."""
        retval = {}
        if "remainingFuelLiters" in fuel_data:
            retval["remaining_fuel"] = ValueWithUnit(fuel_data["remainingFuelLiters"], "L")
        if "remainingFuelPercent" in fuel_data:
            retval["remaining_fuel_percent"] = fuel_data["remainingFuelPercent"]
        if "range" in fuel_data:
            retval["remaining_range_fuel"] = ValueWithUnit(fuel_data["range"], "km")
        return retval

    @staticmethod
    def _parse_electric_data(
        electric_data: Dict, fetched_at: datetime.datetime, charging_window: Optional[Dict] = None
    ) -> Dict:
        """Parse electric data."""
        retval = {}
        if "isChargerConnected" in electric_data:
            retval["is_charger_connected"] = electric_data["isChargerConnected"]
        if "chargingLevelPercent" in electric_data:
            retval["remaining_battery_percent"] = int(electric_data["chargingLevelPercent"])
        if "range" in electric_data:
            retval["remaining_range_electric"] = ValueWithUnit(electric_data["range"], "km")
        if "chargingStatus" in electric_data:
            retval["charging_status"] = ChargingState(
                electric_data["chargingStatus"] if electric_data["chargingStatus"] != "INVALID" else "NOT_CHARGING"
            )
        if "remainingChargingMinutes" in electric_data:
            retval["charging_end_time"] = fetched_at + datetime.timedelta(
                minutes=electric_data["remainingChargingMinutes"]
            )
        if "chargingTarget" in electric_data:
            retval["charging_target"] = int(electric_data["chargingTarget"])

        if retval["charging_status"] == ChargingState.WAITING_FOR_CHARGING and isinstance(charging_window, Dict):
            retval["charging_start_time"] = get_next_occurrence(
                datetime.datetime.now(),
                datetime.time(int(charging_window["start"]["hour"]), int(charging_window["start"]["minute"])),
            )

        return retval
