"""Tests for VehicleSpecs."""

import unittest
from unittest import mock
from test import TEST_COUNTRY, TEST_PASSWORD, TEST_USERNAME, BackendMock, G31_VIN
from bimmer_connected import ConnectedDriveAccount


class TestVehicleSpecs(unittest.TestCase):
    """Tests for VehicleSpecs."""

    def test_update_data_error(self):
        """Test with server returning an error."""
        backend_mock = BackendMock()
        with mock.patch('bimmer_connected.requests', new=backend_mock):
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_COUNTRY)
            vehicle = account.get_vehicle(G31_VIN)
            with self.assertRaises(IOError):
                vehicle.update_state()

    def test_update_data(self):
        """Test with proper data."""
        backend_mock = BackendMock()
        backend_mock.add_response('.*/api/vehicle/specs/v1/{vin}'.format(vin=G31_VIN),
                                  data_file='G31_NBTevo/specs.json')

        with mock.patch('bimmer_connected.requests', new=backend_mock):
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_COUNTRY)
            vehicle = account.get_vehicle(G31_VIN)
            self.assertAlmostEqual(68.0, float(vehicle.specs.TANK_CAPACITY))
