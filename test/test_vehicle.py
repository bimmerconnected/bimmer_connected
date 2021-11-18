"""Tests for ConnectedDriveAccount."""
import re
import unittest

import requests_mock

from bimmer_connected.vehicle import CarBrand, DriveTrainType, VehicleViewDirection

from . import (
    VIN_F11,
    VIN_F31,
    VIN_F35,
    VIN_F44,
    VIN_F45,
    VIN_F48,
    VIN_G05,
    VIN_G08,
    VIN_G21,
    VIN_G30,
    VIN_I01_NOREX,
    VIN_I01_REX,
)
from .test_account import get_mocked_account

ATTRIBUTE_MAPPING = {
    "remainingFuel": "remaining_fuel",
    "position": "gps_position",
    "cbsData": "condition_based_services",
    "checkControlMessages": "check_control_messages",
    "doorLockState": "door_lock_state",
    "updateReason": "last_update_reason",
    "chargingLevelHv": "charging_level_hv",
    "chargingStatus": "charging_status",
    "maxRangeElectric": "max_range_electric",
    "remainingRangeElectric": "remaining_range_electric",
    "parkingLight": "parking_lights",
    "remainingRangeFuel": "remaining_range_fuel",
    "updateTime": "timestamp",
    "chargingTimeRemaining": "charging_time_remaining",
}


class TestVehicle(unittest.TestCase):
    """Tests for ConnectedDriveVehicle."""

    def test_drive_train(self):
        """Tests around drive_train attribute."""
        vehicle = get_mocked_account().get_vehicle(VIN_G21)
        self.assertEqual(DriveTrainType.PLUGIN_HYBRID, vehicle.drive_train)

    def test_parsing_attributes(self):
        """Test parsing different attributes of the vehicle."""
        account = get_mocked_account()

        for vehicle in account.vehicles:
            print(vehicle.name)
            self.assertIsNotNone(vehicle.drive_train)
            self.assertIsNotNone(vehicle.name)
            self.assertIsInstance(vehicle.brand, CarBrand)
            self.assertIsNotNone(vehicle.has_internal_combustion_engine)
            self.assertIsNotNone(vehicle.has_hv_battery)
            self.assertIsNotNone(vehicle.drive_train_attributes)
            self.assertIsNotNone(vehicle.has_weekly_planner_service)

    def test_drive_train_attributes(self):
        """Test parsing different attributes of the vehicle."""
        account = get_mocked_account()

        vehicle_drivetrains = {
            VIN_F11: (True, False, False),
            VIN_F31: (True, False, False),
            VIN_F35: (True, False, False),
            VIN_F44: (True, False, False),
            VIN_F45: (True, True, False),
            VIN_F48: (True, False, False),
            VIN_G05: (True, True, False),
            VIN_G08: (False, True, False),
            VIN_G21: (True, True, False),
            VIN_G30: (True, True, False),
            VIN_I01_NOREX: (False, True, False),
            VIN_I01_REX: (False, True, True),
        }

        for vehicle in account.vehicles:
            self.assertEqual(vehicle_drivetrains[vehicle.vin][0], vehicle.has_internal_combustion_engine)
            self.assertEqual(vehicle_drivetrains[vehicle.vin][1], vehicle.has_hv_battery)
            self.assertEqual(vehicle_drivetrains[vehicle.vin][2], vehicle.has_range_extender)

    def test_parsing_of_lsc_type(self):
        """Test parsing the lsc type field."""
        account = get_mocked_account()

        for vehicle in account.vehicles:
            self.assertIsNotNone(vehicle.lsc_type)

    def test_car_brand(self):
        """Test CarBrand enum"""
        self.assertEqual(CarBrand("BMW"), CarBrand("bmw"))

        with self.assertRaises(ValueError):
            CarBrand("Audi")

    def test_vehicle_attribute_getter(self):
        """Test generic getter."""
        vehicle = get_mocked_account().get_vehicle(VIN_G21)

        self.assertEqual(True, vehicle.has_internal_combustion_engine)

        self.assertEqual("CONNECTED", vehicle.connection_status)

    def test_set_observer_position(self):
        """Test setting observer position"""
        vehicle = get_mocked_account().get_vehicle(VIN_G21)

        vehicle.set_observer_position(12.1, 10.1)

        with self.assertRaises(ValueError):
            vehicle.set_observer_position(12.1, None)

    def test_available_attributes(self):
        """Check that available_attributes returns exactly the arguments we have in our test data."""
        account = get_mocked_account()

        vehicle = account.get_vehicle(VIN_F31)
        self.assertListEqual(["gps_position", "vin"], vehicle.available_attributes)

        vehicle = account.get_vehicle(VIN_G08)
        self.assertListEqual(
            [
                "gps_position",
                "vin",
                "remaining_range_total",
                "mileage",
                "charging_time_remaining",
                "charging_status",
                "charging_level_hv",
                "connection_status",
                "remaining_range_electric",
                "last_charging_end_result",
                "condition_based_services",
                "check_control_messages",
                "door_lock_state",
                "timestamp",
                "last_update_reason",
                "lids",
                "windows",
            ],
            vehicle.available_attributes,
        )

        vehicle = account.get_vehicle(VIN_G30)
        self.assertListEqual(
            [
                "gps_position",
                "vin",
                "remaining_range_total",
                "mileage",
                "charging_time_remaining",
                "charging_status",
                "charging_level_hv",
                "connection_status",
                "remaining_range_electric",
                "last_charging_end_result",
                "remaining_fuel",
                "remaining_range_fuel",
                "fuel_percent",
                "condition_based_services",
                "check_control_messages",
                "door_lock_state",
                "timestamp",
                "last_update_reason",
                "lids",
                "windows",
            ],
            vehicle.available_attributes,
        )

        #     available_attributes = vehicle.available_attributes
        #     print()
        # for vin, dirname in TEST_VEHICLE_DATA.items():
        #     vehicle = account.get_vehicle(vin)
        #     print(vehicle.name)
        #     status_data = load_response_json('{}/status.json'.format(dirname))
        #     existing_attributes = status_data['vehicleStatus'].keys()
        #     existing_attributes = sorted([ATTRIBUTE_MAPPING.get(a, a) for a in existing_attributes
        #                                   if a not in MISSING_ATTRIBUTES])
        #     expected_attributes = sorted([a for a in vehicle.available_attributes if a not in ADDITIONAL_ATTRIBUTES])
        #     self.assertListEqual(existing_attributes, expected_attributes)

    def test_available_state_services(self):
        """Check that available_attributes returns exactly the arguments we have in our test data."""
        vehicle = get_mocked_account().get_vehicle(VIN_F31)

        self.assertListEqual(["status"], vehicle.available_state_services)

    def test_vehicle_image(self):
        """Test vehicle image request."""
        vehicle = get_mocked_account().get_vehicle(VIN_G05)

        with requests_mock.Mocker() as mock:
            mock.get(
                re.compile(r"/eadrax-ics/v3/presentation/vehicles/\w*/images\?carView=\w*"),
                headers={"accept": "image/png"},
                text="png_image",
            )

            self.assertEqual(b"png_image", vehicle.get_vehicle_image(VehicleViewDirection.FRONT))
