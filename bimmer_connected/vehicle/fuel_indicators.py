"""Generals models used for bimmer_connected."""


import datetime
import logging
from dataclasses import dataclass
from typing import Dict, List

from bimmer_connected.vehicle.models import ValueWithUnit, VehicleDataBase

_LOGGER = logging.getLogger(__name__)


@dataclass
class FuelIndicators(VehicleDataBase):  # pylint:disable=too-many-instance-attributes
    """Provides an accessible version of `status.fuelIndicators`."""

    remaining_range_fuel: ValueWithUnit = ValueWithUnit(None, None)
    remaining_range_electric: ValueWithUnit = ValueWithUnit(None, None)
    remaining_range_combined: ValueWithUnit = ValueWithUnit(None, None)
    remaining_charging_time: float = None
    charging_status: str = None
    charging_start_time: datetime.datetime = None
    charging_end_time: datetime.datetime = None
    charging_time_label: str = None

    @classmethod
    def _parse_vehicle_data(cls, vehicle_data: List[Dict]) -> Dict:
        """Parse fuel indicators based on Ids."""
        if "status" not in vehicle_data or "fuelIndicators" not in vehicle_data["status"]:
            _LOGGER.error("Unable to read data from `status.fuelIndicators`.")
            return None

        retval = {}
        fuel_indicators = vehicle_data["status"]["fuelIndicators"]
        for indicator in fuel_indicators:
            if (indicator.get("rangeIconId") or indicator.get("infoIconId")) == 59691:  # Combined
                retval["remaining_range_combined"] = cls._parse_to_tuple(indicator)
            elif (indicator.get("rangeIconId") or indicator.get("infoIconId")) == 59683:  # Electric
                retval["remaining_range_electric"] = cls._parse_to_tuple(indicator)

                retval["charging_time_label"] = indicator["infoLabel"]
                retval["charging_status"] = indicator["chargingStatusType"]

                if indicator.get("chargingStatusType") in ["CHARGING", "PLUGGED_IN"]:
                    retval.update(cls._parse_charging_timestamp(indicator))

            elif (indicator.get("rangeIconId") or indicator.get("infoIconId")) == 59681:  # Fuel
                retval["remaining_range_fuel"] = cls._parse_to_tuple(indicator)

        retval["remaining_range_combined"] = (
            retval.get("remaining_range_combined")
            or retval.get("remaining_range_fuel")
            or retval.get("remaining_range_electric")
        )

        return retval

    @staticmethod
    def _parse_charging_timestamp(indicator: Dict) -> None:
        """Parse charging end time string to timestamp."""
        charging_start_time: datetime.datetime = None
        charging_end_time: datetime.datetime = None
        remaining_charging_time: int = None

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
                remaining_charging_time = (charging_end_time - current_time).seconds
            elif indicator["chargingStatusType"] == "PLUGGED_IN":
                charging_start_time = datetime_parsed
        except ValueError:
            _LOGGER.error("Error parsing charging end time '%s' out of '%s'", time_str, indicator["infoLabel"])
        return {
            "charging_end_time": charging_end_time,
            "charging_start_time": charging_start_time,
            "remaining_charging_time": remaining_charging_time,
        }

    @staticmethod
    def _parse_to_tuple(fuel_indicator):
        """Parse fuel indicator to standard range tuple."""
        try:
            range_val = int(fuel_indicator["rangeValue"])
        except ValueError:
            return ValueWithUnit(None, None)
        return ValueWithUnit(range_val, fuel_indicator["rangeUnits"])
