"""Test for remote_services."""
import unittest
from unittest import mock
import datetime
from test import BackendMock, TEST_USERNAME, TEST_PASSWORD, TEST_COUNTRY, G31_VIN, load_response_json

from bimmer_connected import ConnectedDriveAccount
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

    def test_remove_light_flash(self):
        """Test executing a remote light flash."""
        backend_mock = BackendMock()
        backend_mock.add_response(r'.*/api/vehicle/remoteservices/v1/{vin}/RLF'.format(vin=G31_VIN),
                                  data_file='G31_NBTevo/RLF_INITIAL_RESPONSE.json')

        with mock.patch('bimmer_connected.requests', new=backend_mock):
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_COUNTRY)
            vehicle = account.get_vehicle(G31_VIN)
            vehicle.remote_services.trigger_remote_light_flash()
