"""Generals models used for bimmer_connected."""


import datetime
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from bimmer_connected.models import StrEnum, ValueWithUnit, VehicleDataBase

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
class FuelAndBattery(VehicleDataBase):  # pylint:disable=too-many-instance-attributes
    """Provides an accessible version of `status.FuelAndBattery`."""

    remaining_range_fuel: Optional[ValueWithUnit] = ValueWithUnit(None, None)
    """Get the remaining range of the vehicle on fuel."""

    remaining_range_electric: Optional[ValueWithUnit] = ValueWithUnit(None, None)
    """Get the remaining range of the vehicle on electricity."""

    remaining_fuel: Optional[ValueWithUnit] = ValueWithUnit(None, None)
    """Get the remaining fuel of the vehicle."""

    remaining_fuel_percent: Optional[int] = None
    """State of charge of the high voltage battery in percent."""

    remaining_battery_percent: Optional[int] = None
    """State of charge of the high voltage battery in percent."""

    charging_status: Optional[ChargingState] = None
    """Charging state of the vehicle."""

    charging_start_time_no_tz: Optional[datetime.datetime] = None
    """The planned time the vehicle will start charging without time zone information."""

    charging_end_time: Optional[datetime.datetime] = None
    """The estimated time the vehicle will have finished charging."""

    is_charger_connected: bool = False
    """Get status of the connection"""

    account_timezone: datetime.timezone = datetime.timezone.utc

    @property
    def remaining_range_total(self) -> Optional[ValueWithUnit]:
        """Get the total remaining range of the vehicle (fuel + electricity, if available)."""
        fuel = self.remaining_range_fuel
        electric = self.remaining_range_electric
        if fuel and not fuel.value:
            return electric
        if electric and not electric.value:
            return fuel
        unit = fuel.unit or electric.unit  # type: ignore[union-attr]
        total = (fuel.value or 0) + (electric.value or 0)  # type: ignore[union-attr]
        return ValueWithUnit(total, unit)

    @property
    def charging_start_time(self) -> Optional[datetime.datetime]:
        """The planned time the vehicle will start charging."""
        if self.charging_start_time_no_tz:
            return self.charging_start_time_no_tz.astimezone(self.account_timezone)
        return None

    # pylint:disable=arguments-differ
    @classmethod
    def from_vehicle_data(cls, vehicle_data: Dict):
        """Creates the class based on vehicle data from API."""
        parsed = cls._parse_vehicle_data(vehicle_data) or {}
        if len(parsed) > 0:
            return cls(**parsed)
        return None

    @classmethod
    def _parse_vehicle_data(cls, vehicle_data: Dict) -> Optional[Dict]:
        """Parse fuel indicators based on Ids."""
        retval: Dict[str, Any] = {}

        state = vehicle_data.get("state", {})

        fuel_data = state.get("combustionFuelLevel", {})
        if fuel_data:
            retval.update(cls._parse_fuel_data(fuel_data))

        electric_data = state.get("electricChargingState", {})
        if electric_data:
            retval.update(
                cls._parse_electric_data(
                    electric_data,
                    vehicle_data["fetched_at"],
                    state.get("chargingProfile", {}).get("reductionOfChargeCurrent"),
                ),
            )

        if "remaining_fuel" in retval:
            retval["remaining_fuel"] = ValueWithUnit(
                retval["remaining_fuel"], "L" if vehicle_data["is_metric"] else "gal"
            )
        if "remaining_range_fuel" in retval:
            retval["remaining_range_fuel"] = ValueWithUnit(
                retval["remaining_range_fuel"], "km" if vehicle_data["is_metric"] else "mi"
            )
        if "remaining_range_electric" in retval:
            retval["remaining_range_electric"] = ValueWithUnit(
                retval["remaining_range_electric"], "km" if vehicle_data["is_metric"] else "mi"
            )

        return retval

    @staticmethod
    def _parse_fuel_data(fuel_data: Dict) -> Dict:
        """Parse fuel data."""
        retval = {}
        if "remainingFuelLiters" in fuel_data:
            retval["remaining_fuel"] = fuel_data["remainingFuelLiters"]
        if "remainingFuelPercent" in fuel_data:
            retval["remaining_fuel_percent"] = fuel_data["remainingFuelPercent"]
        if "range" in fuel_data:
            retval["remaining_range_fuel"] = fuel_data["range"]
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
            retval["remaining_range_electric"] = electric_data["range"]
        if "chargingStatus" in electric_data:
            retval["charging_status"] = ChargingState(
                electric_data["chargingStatus"] if electric_data["chargingStatus"] != "INVALID" else "NOT_CHARGING"
            )
        if "remainingChargingMinutes" in electric_data:
            retval["charging_end_time"] = fetched_at + datetime.timedelta(
                minutes=electric_data["remainingChargingMinutes"]
            )

        if retval["charging_status"] == ChargingState.WAITING_FOR_CHARGING and isinstance(charging_window, Dict):
            retval["charging_start_time_no_tz"] = datetime.datetime.combine(
                datetime.datetime.now().date(),
                datetime.time(int(charging_window["start"]["hour"]), int(charging_window["start"]["minute"])),
            )

        return retval
