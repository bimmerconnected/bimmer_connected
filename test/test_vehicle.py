"""Tests for ConnectedDriveVehicle."""
import unittest
from unittest import mock
from test import load_response_json, BackendMock, TEST_USERNAME, TEST_PASSWORD, TEST_REGION, \
    G31_VIN, F48_VIN, I01_VIN, I01_NOREX_VIN, F15_VIN, F45_VIN

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
            self.assertIsNotNone(vehicle.statistics_available)

    def test_drive_train_attributes(self):
        """Test parsing different attributes of the vehicle."""
        backend_mock = BackendMock()
        with mock.patch('bimmer_connected.account.requests', new=backend_mock):
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)

        for vehicle in account.vehicles:
            print(vehicle.name)
            self.assertEqual(vehicle.vin in [G31_VIN, F48_VIN, F15_VIN, I01_VIN, F45_VIN],
                             vehicle.has_internal_combustion_engine)
            self.assertEqual(vehicle.vin in [I01_VIN, I01_NOREX_VIN, F45_VIN],
                             vehicle.has_hv_battery)

    def test_statistics_available(self):
        """Test parsing the statistics_available field."""
        backend_mock = BackendMock()
        with mock.patch('bimmer_connected.account.requests', new=backend_mock):
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)
        g31 = account.get_vehicle(G31_VIN)
        f45 = account.get_vehicle(F45_VIN)

        self.assertFalse(g31.statistics_available)
        self.assertTrue(f45.statistics_available)
