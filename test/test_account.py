"""Tests for ConnectedDriveAccount."""
import json
import unittest
from unittest import mock
from test import BackendMock, G31_VIN
from bimmer_connected.account import ConnectedDriveAccount
from bimmer_connected.country_selector import Regions

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
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, Regions.REST_OF_WORLD)
            self.assertIsNotNone(account._oauth_token)
            self.assertEqual(5, len(account.vehicles))
            vehicle = account.get_vehicle(G31_VIN)
            self.assertEqual(G31_VIN, vehicle.vin)

            self.assertIsNone(account.get_vehicle('invalid_vin'))

    def test_invalid_send_response(self):
        """Test parsing the results of an invalid request"""
        backend_mock = BackendMock()
        with mock.patch('bimmer_connected.account.requests', new=backend_mock):
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, Regions.REST_OF_WORLD)
            with self.assertRaises(IOError):
                account.send_request('invalid_url')

    def test_us_header(self):
        """Test if the host is set correctly in the request."""
        backend_mock = BackendMock()
        with mock.patch('bimmer_connected.account.requests', new=backend_mock):
            ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, Regions.NORTH_AMERICA)
            request = [r for r in backend_mock.last_request if 'oauth' in r.url][0]
            self.assertEqual('b2vapi.bmwgroup.us', request.headers['Host'])

    def test_anonymize_data(self):
        """Test anonymization function."""
        test_dict = {
            'vin': 'secret',
            'a sub-dict': {
                'lat': 666,
                'lon': 666,
                'heading': 666,
            },
            'licensePlate': 'secret',
            'public': 'public_data',
            'a_list': [
                {'vin': 'secret'},
                {
                    'lon': 666,
                    'public': 'more_public_data',
                },
            ]
        }
        anon_text = json.dumps(ConnectedDriveAccount._anonymize_data(test_dict))
        self.assertNotIn('secret', anon_text)
        self.assertNotIn('666', anon_text)
        self.assertIn('public_data', anon_text)
        self.assertIn('more_public_data', anon_text)
