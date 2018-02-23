"""Test for remote_services."""
import unittest
from unittest import mock
import datetime
from test import BackendMock, TEST_USERNAME, TEST_PASSWORD, TEST_COUNTRY, G31_VIN, load_response_json

from bimmer_connected.account import ConnectedDriveAccount
from bimmer_connected.remote_services import RemoteServiceStatus, ExecutionState
from bimmer_connected import remote_services


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
        remote_services._POLLING_CYCLE = 0
        remote_services._UPDATE_AFTER_REMOTE_SERVICE_DELAY = 0

        services = [
            ('RLF', 'trigger_remote_light_flash', False),
            ('RDL', 'trigger_remote_door_lock', True),
            ('RDU', 'trigger_remote_door_unlock', True),
            ('RCN', 'trigger_remote_air_conditioning', True),
            ('RHB', 'trigger_remote_horn', False)
        ]

        for service, call, triggers_update in services:
            backend_mock = BackendMock()

            with mock.patch('bimmer_connected.account.requests', new=backend_mock):
                backend_mock.add_response(r'.*/api/vehicle/remoteservices/v1/{vin}/{service}'.format(
                    vin=G31_VIN, service=service), data_files=['G31_NBTevo/RLF_INITIAL_RESPONSE.json'])

                backend_mock.add_response(
                    '.*/api/vehicle/remoteservices/v1/{vin}/state/execution'.format(vin=G31_VIN),
                    data_files=[
                        'G31_NBTevo/RLF_PENDING.json',
                        'G31_NBTevo/RLF_DELIVERED.json',
                        'G31_NBTevo/RLF_EXECUTED.json'])

                backend_mock.add_response('.*/api/vehicle/dynamic/v1/{vin}'.format(vin=G31_VIN),
                                          data_files=['G31_NBTevo/dynamic.json'])

                backend_mock.add_response('.*/api/vehicle/specs/v1/{vin}'.format(vin=G31_VIN),
                                          data_files=['G31_NBTevo/specs.json'])

                account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_COUNTRY)
                mock_listener = mock.Mock(return_value=None)
                account.add_update_listener(mock_listener)
                vehicle = account.get_vehicle(G31_VIN)

                response = getattr(vehicle.remote_services, call)()
                self.assertEqual(ExecutionState.EXECUTED, response.state)

                if triggers_update:
                    mock_listener.assert_called_once_with()
                else:
                    mock_listener.assert_not_called()

    def test_get_remote_service_status(self):
        """Test get_remove_service_status method."""
        backend_mock = BackendMock()

        with mock.patch('bimmer_connected.account.requests', new=backend_mock):
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_COUNTRY)
            vehicle = account.get_vehicle(G31_VIN)
            with self.assertRaises(IOError):
                vehicle.remote_services._get_remote_service_status()

            backend_mock.add_response(
                '.*/api/vehicle/remoteservices/v1/{vin}/state/execution'.format(vin=G31_VIN),
                data_files=['G31_NBTevo/RLF_EXECUTED.json'])
            status = vehicle.remote_services._get_remote_service_status()
            self.assertEqual(ExecutionState.EXECUTED, status.state)
