"""Tests for ConnectedDriveAccount."""
import json
import unittest
from unittest import mock
from test import BackendMock, G31_VIN, TEST_USERNAME, TEST_PASSWORD, TEST_REGION
from bimmer_connected.account import ConnectedDriveAccount
from bimmer_connected.country_selector import Regions


class TestAccount(unittest.TestCase):
    """Tests for ConnectedDriveAccount."""

    # pylint: disable=protected-access

    def test_token_vehicles(self):
        """Test getting backend token and vehicle list."""
        backend_mock = BackendMock()
        with mock.patch('bimmer_connected.account.requests', new=backend_mock):
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, Regions.REST_OF_WORLD)
            self.assertIsNotNone(account._oauth_token)
            self.assertEqual(6, len(account.vehicles))
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
                }
            ],
            'b_list': ['a', 'b'],
            'empty_list': [],
        }
        anon_text = json.dumps(ConnectedDriveAccount._anonymize_data(test_dict))
        self.assertNotIn('secret', anon_text)
        self.assertNotIn('666', anon_text)
        self.assertIn('public_data', anon_text)
        self.assertIn('more_public_data', anon_text)

    def test_vehicle_search_case(self):
        """Check if the search for the vehicle by VIN is NOT case sensitive."""
        backend_mock = BackendMock()
        with mock.patch('bimmer_connected.account.requests', new=backend_mock):
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)

        vin = account.vehicles[1].vin
        self.assertEqual(vin, account.get_vehicle(vin).vin)
        self.assertEqual(vin, account.get_vehicle(vin.lower()).vin)
        self.assertEqual(vin, account.get_vehicle(vin.upper()).vin)

    def test_set_observer_value(self):
        """Test set_observer_position with valid arguments."""
        backend_mock = BackendMock()
        with mock.patch('bimmer_connected.account.requests', new=backend_mock):
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, Regions.REST_OF_WORLD)

            account.set_observer_position(1.0, 2.0)
            for vehicle in account.vehicles:
                self.assertEqual(vehicle.observer_latitude, 1.0)
                self.assertEqual(vehicle.observer_longitude, 2.0)

    def test_set_observer_not_set(self):
        """Test set_observer_position with no arguments."""
        backend_mock = BackendMock()
        with mock.patch('bimmer_connected.account.requests', new=backend_mock):
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, Regions.REST_OF_WORLD)

            for vehicle in account.vehicles:
                self.assertEqual(vehicle.observer_latitude, 0.0)
                self.assertEqual(vehicle.observer_longitude, 0.0)

            account.set_observer_position(None, None)

            for vehicle in account.vehicles:
                self.assertEqual(vehicle.observer_latitude, 0.0)
                self.assertEqual(vehicle.observer_longitude, 0.0)

    def test_set_observer_some_none(self):
        """Test set_observer_position with invalid arguments."""
        backend_mock = BackendMock()
        with mock.patch('bimmer_connected.account.requests', new=backend_mock):
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, Regions.REST_OF_WORLD)

            with self.assertRaises(ValueError):
                account.set_observer_position(None, 2.0)

            with self.assertRaises(ValueError):
                account.set_observer_position(1.0, None)
