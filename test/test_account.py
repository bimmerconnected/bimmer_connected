"""Tests for ConnectedDriveAccount."""
import unittest
from unittest import mock
from test import BackendMock
from bimmer_connected import ConnectedDriveAccount

TEST_USERNAME = 'some_user'
TEST_PASSWORD = 'my_secret'
TEST_COUNTRY = 'Germany'


class TestAccount(unittest.TestCase):
    """Tests for ConnectedDriveAccount."""

    # pylint: disable=protected-access

    def test_token_vehicles(self):
        """Test getting backend token and vehicle list."""
        backend_mock = BackendMock()
        with mock.patch('bimmer_connected.requests', new=backend_mock):
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_COUNTRY)
            self.assertIsNotNone(account._oauth_token)
            vehicles = account.vehicles
            self.assertEqual(1, len(vehicles))
            self.assertEqual(vehicles[0].vin, 'G31_NBTEvo_VIN')
