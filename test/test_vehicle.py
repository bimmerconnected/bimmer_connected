"""Tests for ConnectedDriveVehicle."""
import unittest
from unittest import mock
from test import load_response_json, BackendMock, TEST_USERNAME, TEST_PASSWORD, TEST_COUNTRY

from bimmer_connected.vehicle import ConnectedDriveVehicle, DriveTrainType
from bimmer_connected.account import ConnectedDriveAccount

G31_VEHICLE = load_response_json('vehicles.json')[0]
F48_VEHICLE = load_response_json('vehicles.json')[1]
I01_VEHICLE = load_response_json('vehicles.json')[3]


class TestVehicle(unittest.TestCase):
    """Tests for ConnectedDriveVehicle."""

    def test_has_rex(self):
        """Tests around hasRex attribute."""
        vehicle = ConnectedDriveVehicle(None, G31_VEHICLE)
        self.assertFalse(vehicle.has_rex)
        vehicle.attributes['hasRex'] = '1'
        self.assertTrue(vehicle.has_rex)

    def test_drive_train(self):
        """Tests around drive_train attribute."""
        vehicle = ConnectedDriveVehicle(None, G31_VEHICLE)
        self.assertEqual(DriveTrainType.CONVENTIONAL, vehicle.drive_train)

        vehicle = ConnectedDriveVehicle(None, F48_VEHICLE)
        self.assertEqual(DriveTrainType.PHEV, vehicle.drive_train)

        vehicle = ConnectedDriveVehicle(None, I01_VEHICLE)
        self.assertEqual(DriveTrainType.BEV, vehicle.drive_train)

    def test_parsing_attributes(self):
        """Test parsing different attributes of the vehicle."""
        backend_mock = BackendMock()
        with mock.patch('bimmer_connected.account.requests', new=backend_mock):
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_COUNTRY)

        for vehicle in account.vehicles:
            self.assertIsNotNone(vehicle.drive_train)
            self.assertIsNotNone(vehicle.name)
            self.assertIsNotNone(vehicle.has_rex)
