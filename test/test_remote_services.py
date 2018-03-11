"""Test for remote_services."""
import unittest
from unittest import mock
import datetime
from test import BackendMock, TEST_USERNAME, TEST_PASSWORD, TEST_REGION, G31_VIN, load_response_json

from bimmer_connected.account import ConnectedDriveAccount
from bimmer_connected.remote_services import RemoteServiceStatus, ExecutionState
from bimmer_connected import remote_services

_RESPONSE_INITIATED = 'G31_NBTevo/flash_initiated.json'
_RESPONSE_PENDING = 'G31_NBTevo/flash_pending.json'
_RESPONSE_DELIVERED = 'G31_NBTevo/flash_delivered.json'
_RESPONSE_EXECUTED = 'G31_NBTevo/flash_executed.json'


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
        rss = RemoteServiceStatus(load_response_json(_RESPONSE_INITIATED))
        self.assertEqual(ExecutionState.INITIATED, rss.state)

        rss = RemoteServiceStatus(load_response_json(_RESPONSE_PENDING))
        self.assertEqual(ExecutionState.PENDING, rss.state)

        rss = RemoteServiceStatus(load_response_json(_RESPONSE_DELIVERED))
        self.assertEqual(ExecutionState.DELIVERED, rss.state)

        rss = RemoteServiceStatus(load_response_json(_RESPONSE_EXECUTED))
        self.assertEqual(ExecutionState.EXECUTED, rss.state)

    def test_trigger_remote_services(self):
        """Test executing a remote light flash."""
        remote_services._POLLING_CYCLE = 0
        remote_services._UPDATE_AFTER_REMOTE_SERVICE_DELAY = 0

        services = [
            ('LIGHT_FLASH', 'trigger_remote_light_flash', False),
            ('DOOR_LOCK', 'trigger_remote_door_lock', True),
            ('DOOR_UNLOCK', 'trigger_remote_door_unlock', True),
            ('CLIMATE_NOW', 'trigger_remote_air_conditioning', True),
            ('HORN_BLOW', 'trigger_remote_horn', False)
        ]

        for service, call, triggers_update in services:
            backend_mock = BackendMock()
            backend_mock.setup_default_vehicles()

            backend_mock.add_response('https://.+/webapi/v1/user/vehicles/{vin}/executeService'.format(vin=G31_VIN),
                                      data_files=[_RESPONSE_INITIATED])

            backend_mock.add_response(
                r'https://.+/webapi/v1/user/vehicles/{vin}/serviceExecutionStatus\?serviceType={service_type}'.format(
                    vin=G31_VIN, service_type=service),
                data_files=[
                    _RESPONSE_PENDING,
                    _RESPONSE_PENDING,
                    _RESPONSE_DELIVERED,
                    _RESPONSE_DELIVERED,
                    _RESPONSE_EXECUTED])

            with mock.patch('bimmer_connected.account.requests', new=backend_mock):
                account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)
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
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)
            vehicle = account.get_vehicle(G31_VIN)
            with self.assertRaises(IOError):
                vehicle.remote_services._get_remote_service_status(remote_services._Services.REMOTE_LIGHT_FLASH)

            backend_mock.add_response(
                r'https://.+/webapi/v1/user/vehicles/{vin}/serviceExecutionStatus\?.+'.format(vin=G31_VIN),
                data_files=['G31_NBTevo/flash_executed.json'])
            status = vehicle.remote_services._get_remote_service_status(remote_services._Services.REMOTE_LIGHT_FLASH)
            self.assertEqual(ExecutionState.EXECUTED, status.state)
