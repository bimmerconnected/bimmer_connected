"""Tests for ConnectedDriveAccount."""
import unittest
from unittest import mock
from test import BackendMock
from bimmer_connected.account import ConnectedDriveAccount

TEST_USERNAME = 'some_user'
TEST_PASSWORD = 'my_secret'
TEST_COUNTRY = 'Germany'


class TestAccount(unittest.TestCase):
    """Tests for ConnectedDriveAccount."""

    # pylint: disable=protected-access

    def test_token_vehicles(self):
        """Test getting backend token and vehicle list."""
        backend_mock = BackendMock()
        with mock.patch('bimmer_connected.account.requests', new=backend_mock):
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_COUNTRY)
            self.assertIsNotNone(account._oauth_token)
            self.assertEqual(2, len(account.vehicles))
            vin = 'G31_NBTEvo_VIN'
            vehicle = account.get_vehicle(vin)
            self.assertEqual(vehicle.vin, vin)

    def test_invalid_send_response(self):
        """Test parsing the results of an invalid request"""
        backend_mock = BackendMock()
        with mock.patch('bimmer_connected.account.requests', new=backend_mock):
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_COUNTRY)
            with self.assertRaises(IOError):
                account.send_request('invalid_url')
