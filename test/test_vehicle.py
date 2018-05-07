"""Tests for ConnectedDriveVehicle."""
import unittest
from unittest import mock
from test import load_response_json, BackendMock, TEST_USERNAME, TEST_PASSWORD, TEST_REGION, \
    G31_VIN, F48_VIN, I01_VIN, I01_NOREX_VIN, F15_VIN, F45_VIN, TEST_VEHICLE_DATA, \
    ATTRIBUTE_MAPPING, MISSING_ATTRIBUTES, ADDITIONAL_ATTRIBUTES

from bimmer_connected.vehicle import ConnectedDriveVehicle, DriveTrainType
from bimmer_connected.account import ConnectedDriveAccount


_VEHICLES = load_response_json('vehicles.json')['vehicles']
G31_VEHICLE = _VEHICLES[0]


class TestVehicle(unittest.TestCase):
    """Tests for ConnectedDriveVehicle."""

    def test_drive_train(self):
        """Tests around drive_train attribute."""
        vehicle = ConnectedDriveVehicle(None, G31_VEHICLE)
        self.assertEqual(DriveTrainType.CONVENTIONAL, vehicle.drive_train)

    def test_parsing_attributes(self):
        """Test parsing different attributes of the vehicle."""
        backend_mock = BackendMock()
        with mock.patch('bimmer_connected.account.requests', new=backend_mock):
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)

        for vehicle in account.vehicles:
            print(vehicle.name)
            self.assertIsNotNone(vehicle.drive_train)
            self.assertIsNotNone(vehicle.name)
            self.assertIsNotNone(vehicle.has_internal_combustion_engine)
            self.assertIsNotNone(vehicle.has_hv_battery)
            self.assertIsNotNone(vehicle.drive_train_attributes)

    def test_drive_train_attributes(self):
        """Test parsing different attributes of the vehicle."""
        backend_mock = BackendMock()
        with mock.patch('bimmer_connected.account.requests', new=backend_mock):
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)

        for vehicle in account.vehicles:
            print(vehicle.name)
            self.assertEqual(vehicle.vin in [G31_VIN, F48_VIN, F15_VIN, I01_VIN, F45_VIN],
                             vehicle.has_internal_combustion_engine)
            self.assertEqual(vehicle.vin in [I01_VIN, I01_NOREX_VIN],
                             vehicle.has_hv_battery)

    def test_parsing_of_lsc_type(self):
        """Test parsing the lsc type field."""
        backend_mock = BackendMock()
        with mock.patch('bimmer_connected.account.requests', new=backend_mock):
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)

        for vehicle in account.vehicles:
            self.assertIsNotNone(vehicle.lsc_type)

    def test_available_attributes(self):
        """Check that available_attributes returns exactly the arguments we have in our test data."""
        backend_mock = BackendMock()
        with mock.patch('bimmer_connected.account.requests', new=backend_mock):
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)

        for vin, dirname in TEST_VEHICLE_DATA.items():
            vehicle = account.get_vehicle(vin)
            print(vehicle.name)
            status_data = load_response_json('{}/status.json'.format(dirname))
            existing_attributes = status_data['vehicleStatus'].keys()
            existing_attributes = sorted([ATTRIBUTE_MAPPING.get(a, a) for a in existing_attributes
                                          if a not in MISSING_ATTRIBUTES])
            expected_attributes = sorted([a for a in vehicle.available_attributes if a not in ADDITIONAL_ATTRIBUTES])
            self.assertListEqual(existing_attributes, expected_attributes)
