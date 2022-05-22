"""Generals models used for bimmer_connected."""


import datetime
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from bimmer_connected.vehicle.models import StrEnum, ValueWithUnit, VehicleDataBase

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


@dataclass
class FuelAndBattery(VehicleDataBase):  # pylint:disable=too-many-instance-attributes
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
    """The planned time the vehicle will start charging."""

    charging_end_time: Optional[datetime.datetime] = None
    """The estimated time the vehicle will have finished charging."""

    charging_time_label: Optional[str] = None
    """The planned start/estimated end time as provided by the API."""

    is_charger_connected: bool = False
    """Get status of the connection"""

    account_timezone: datetime.timezone = datetime.timezone.utc

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

        properties = vehicle_data.get("properties", {})

        fuel_level = properties.get("fuelLevel", {})
        if fuel_level:
            retval["remaining_fuel"] = ValueWithUnit(
                fuel_level.get("value"),
                fuel_level.get("units"),
            )

        if properties.get("fuelPercentage", {}).get("value"):
            retval["remaining_fuel_percent"] = int(properties.get("fuelPercentage", {}).get("value"))

        if "chargingState" in properties:
            retval["remaining_battery_percent"] = int(properties["chargingState"].get("chargePercentage") or 0)
            retval["is_charger_connected"] = properties["chargingState"].get("isChargerConnected", False)

        # Only parse ranges if vehicle has enabled LSC
        if "capabilities" in vehicle_data and vehicle_data["capabilities"]["lastStateCall"]["lscState"] == "ACTIVATED":
            fuel_indicators = vehicle_data.get("status", {}).get("fuelIndicators", [])
            for indicator in fuel_indicators:
                if (indicator.get("rangeIconId") or indicator.get("infoIconId")) == 59691:  # Combined
                    retval["remaining_range_total"] = cls._parse_to_tuple(indicator)
                elif (indicator.get("rangeIconId") or indicator.get("infoIconId")) == 59683:  # Electric
                    retval["remaining_range_electric"] = cls._parse_to_tuple(indicator)

                    retval["charging_time_label"] = indicator["infoLabel"]
                    retval["charging_status"] = ChargingState(
                        indicator["chargingStatusType"]
                        if indicator["chargingStatusType"] != "DEFAULT"
                        else "NOT_CHARGING"
                    )

                    if indicator.get("chargingStatusType") in ["CHARGING", "PLUGGED_IN"]:
                        retval.update(cls._parse_charging_timestamp(indicator))

                elif (indicator.get("rangeIconId") or indicator.get("infoIconId")) == 59681:  # Fuel
                    retval["remaining_range_fuel"] = cls._parse_to_tuple(indicator)

            retval["remaining_range_total"] = (
                retval.get("remaining_range_total")
                or retval.get("remaining_range_fuel")
                or retval.get("remaining_range_electric")
            )

        return retval

    def _update_after_parse(self, parsed: Dict) -> Dict:
        """Updates parsed vehicle data with attributes stored in class if needed."""
        if parsed.get("charging_end_time"):
            parsed["charging_end_time"] = parsed["charging_end_time"].replace(tzinfo=self.account_timezone)
        if parsed.get("charging_start_time"):
            parsed["charging_start_time"] = parsed["charging_start_time"].replace(tzinfo=self.account_timezone)
        return parsed

    @staticmethod
    def _parse_charging_timestamp(indicator: Dict) -> Dict:
        """Parse charging end time string to timestamp."""
        charging_start_time: Optional[datetime.datetime] = None
        charging_end_time: Optional[datetime.datetime] = None

        # Only calculate charging end time if infolabel is like '100% at ~11:04am'
        # Other options: 'Charging', 'Starts at ~09:00am' (but not handled here)

        time_str = indicator["infoLabel"].split("~")[-1].strip()
        try:
            time_parsed = datetime.datetime.strptime(time_str, "%I:%M %p")

            current_time = datetime.datetime.now()
            datetime_parsed = time_parsed.replace(
                year=current_time.year, month=current_time.month, day=current_time.day
            )
            if datetime_parsed < current_time:
                datetime_parsed = datetime_parsed + datetime.timedelta(days=1)

            if indicator["chargingStatusType"] == "CHARGING":
                charging_end_time = datetime_parsed
            elif indicator["chargingStatusType"] == "PLUGGED_IN":
                charging_start_time = datetime_parsed
        except ValueError:
            _LOGGER.error("Error parsing charging end time '%s' out of '%s'", time_str, indicator["infoLabel"])
        return {
            "charging_end_time": charging_end_time,
            "charging_start_time": charging_start_time,
        }

    @staticmethod
    def _parse_to_tuple(fuel_indicator):
        """Parse fuel indicator to standard range tuple."""
        try:
            # A value of '- -' apparently means zero
            range_value = fuel_indicator["rangeValue"] if fuel_indicator["rangeValue"] != "- -" else 0
            range_val = int(range_value)
        except ValueError:
            return ValueWithUnit(None, None)
        return ValueWithUnit(range_val, fuel_indicator["rangeUnits"])
