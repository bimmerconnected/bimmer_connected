"""Test for remote_services."""
import unittest
from unittest import mock
import datetime
from test import BackendMock, TEST_USERNAME, TEST_PASSWORD, TEST_COUNTRY, G31_VIN, load_response_json

from bimmer_connected.account import ConnectedDriveAccount
from bimmer_connected.remote_services import RemoteServiceStatus, ExecutionState


class TestRemoteServices(unittest.TestCase):
    """Test for remote_services."""

    # pylint: disable=protected-access

    def test_parse_timestamp(self):
        """Test parsing the timestamp format."""
        timestamp = RemoteServiceStatus._parse_timestamp("2018-02-11T15:10:39.465+01")
        expected = datetime.datetime(year=2018, month=2, day=11, hour=15, minute=10, second=39, microsecond=465000)
        self.assertEqual(expected, timestamp)

    def test_states(self):
        """Test parsing the different response types."""
        rss = RemoteServiceStatus(load_response_json('G31_NBTevo/RLF_INITIAL_RESPONSE.json'))
        self.assertEqual(ExecutionState.PENDING, rss.state)

        rss = RemoteServiceStatus(load_response_json('G31_NBTevo/RLF_PENDING.json'))
        self.assertEqual(ExecutionState.PENDING, rss.state)

        rss = RemoteServiceStatus(load_response_json('G31_NBTevo/RLF_DELIVERED.json'))
        self.assertEqual(ExecutionState.DELIVERED, rss.state)

        rss = RemoteServiceStatus(load_response_json('G31_NBTevo/RLF_EXECUTED.json'))
        self.assertEqual(ExecutionState.EXECUTED, rss.state)

    def test_trigger_remote_services(self):
        """Test executing a remote light flash."""
        backend_mock = BackendMock()
        for service in ['RLF', 'RDU', 'RDL']:
            backend_mock.add_response(r'.*/api/vehicle/remoteservices/v1/{vin}/{service}'.format(
                vin=G31_VIN, service=service),
                                      data_file='G31_NBTevo/RLF_INITIAL_RESPONSE.json')

        with mock.patch('bimmer_connected.account.requests', new=backend_mock):
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_COUNTRY)
            vehicle = account.get_vehicle(G31_VIN)

            response = vehicle.remote_services.trigger_remote_light_flash()
            self.assertEqual(ExecutionState.PENDING, response.state)
            self.assertIn('/RLF', backend_mock.last_request.url)

            response = vehicle.remote_services.trigger_remote_door_lock()
            self.assertEqual(ExecutionState.PENDING, response.state)
            self.assertIn('/RDL', backend_mock.last_request.url)

            response = vehicle.remote_services.trigger_remote_door_unlock()
            self.assertEqual(ExecutionState.PENDING, response.state)
            self.assertIn('/RDU', backend_mock.last_request.url)

    def test_get_remote_service_status(self):
        """Test get_remove_service_status method."""
        backend_mock = BackendMock()
        with mock.patch('bimmer_connected.account.requests', new=backend_mock):
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_COUNTRY)
            vehicle = account.get_vehicle(G31_VIN)
            with self.assertRaises(IOError):
                vehicle.remote_services.get_remote_service_status()

            backend_mock.add_response(
                '-*/api/vehicle/remoteservices/v1/{vin}/state/execution'.format(vin=G31_VIN),
                data_file='G31_NBTevo/RLF_EXECUTED.json')
            status = vehicle.remote_services.get_remote_service_status()
            self.assertEqual(ExecutionState.EXECUTED, status.state)
