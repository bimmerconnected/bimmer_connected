"""Test for remote_services."""
import unittest
from unittest import mock
import datetime
from test import BackendMock, TEST_USERNAME, TEST_PASSWORD, TEST_REGION, G31_VIN, load_response_json, \
    POI_DATA, POI_REQUEST, MESSAGE_DATA, MESSAGE_REQUEST

from bimmer_connected.account import ConnectedDriveAccount
from bimmer_connected.remote_services import RemoteServiceStatus, ExecutionState, PointOfInterest, Message
from bimmer_connected import remote_services

_RESPONSE_UNKNOWN = 'G31_NBTevo/flash_unknown.json'
_RESPONSE_INITIATED = 'G31_NBTevo/flash_initiated.json'
_RESPONSE_PENDING = 'G31_NBTevo/flash_pending.json'
_RESPONSE_DELIVERED = 'G31_NBTevo/flash_delivered.json'
_RESPONSE_EXECUTED = 'G31_NBTevo/flash_executed.json'
_MSG_EXECUTED = 'G31_NBTevo/msg_executed.json'


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
        rss = RemoteServiceStatus(load_response_json(_RESPONSE_UNKNOWN))
        self.assertEqual(ExecutionState.UNKNOWN, rss.state)

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
            ('VEHICLE_FINDER', 'trigger_remote_vehicle_finder', True),
            ('HORN_BLOW', 'trigger_remote_horn', False),
            ('SEND_MESSAGE', 'trigger_send_message', False),
            ('SEND_POI', 'trigger_send_poi', False),
        ]

        for service, call, triggers_update in services:
            backend_mock = BackendMock()
            backend_mock.setup_default_vehicles()

            backend_mock.add_response('https://.+/webapi/v1/user/vehicles/{vin}/executeService'.format(vin=G31_VIN),
                                      data_files=[_RESPONSE_INITIATED])

            backend_mock.add_response(
                r'https://.+/webapi/v1/user/vehicles/{vin}/serviceExecutionStatus\?serviceType={service_type}'.format(
                    vin=G31_VIN, service_type=service),
                r'https://.+/webapi/v1/user/vehicles/{vin}/status'.format(
                    vin=G31_VIN),
                data_files=[
                    _RESPONSE_UNKNOWN,
                    _RESPONSE_PENDING,
                    _RESPONSE_PENDING,
                    _RESPONSE_DELIVERED,
                    _RESPONSE_DELIVERED,
                    _RESPONSE_EXECUTED])

            backend_mock.add_response(
                r'https://.+/webapi/v1/user/vehicles/{vin}/status'.format(
                    vin=G31_VIN),
                data_files=[_RESPONSE_EXECUTED])

            backend_mock.add_response(
                r'https://.+/webapi/v1/user/vehicles/{vin}/sendpoi'.format(
                    vin=G31_VIN),
                data_files=[_MSG_EXECUTED],
                status_code=204)

            with mock.patch('bimmer_connected.account.requests', new=backend_mock):
                account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)
                mock_listener = mock.Mock(return_value=None)
                account.add_update_listener(mock_listener)
                vehicle = account.get_vehicle(G31_VIN)

                if service == 'SEND_MESSAGE':
                    response = getattr(vehicle.remote_services, call)(MESSAGE_DATA)
                elif service == 'SEND_POI':
                    response = getattr(vehicle.remote_services, call)(POI_DATA)
                else:
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

    def test_parsing_of_poi_min_attributes(self):
        """Check that a PointOfInterest can be constructed using only latitude & longitude."""
        poi = PointOfInterest(POI_DATA["lat"], POI_DATA["lon"])
        msg = Message.from_poi(poi)
        self.assertEqual(msg.as_server_request, POI_REQUEST["min"])

    def test_parsing_of_poi_all_attributes(self):
        """Check that a PointOfInterest can be constructed using all attributes."""
        poi = PointOfInterest(POI_DATA["lat"], POI_DATA["lon"], name=POI_DATA["name"],
                              additional_info=POI_DATA["additional_info"], street=POI_DATA["street"],
                              city=POI_DATA["city"], postal_code=POI_DATA["postal_code"],
                              country=POI_DATA["country"], website=POI_DATA["website"],
                              phone_numbers=POI_DATA["phone_numbers"])
        msg = Message.from_poi(poi)
        self.assertEqual(msg.as_server_request, POI_REQUEST["all"])

    def test_parsing_of_message_min_attributes(self):
        """Check that a Message can be constructed using text."""
        msg = Message.from_text(MESSAGE_DATA["text"])
        self.assertEqual(msg.as_server_request, MESSAGE_REQUEST["min"])

    def test_parsing_of_message_all_attributes(self):
        """Check that a Message can be constructed using text."""
        msg = Message.from_text(MESSAGE_DATA["text"], MESSAGE_DATA["subject"])
        self.assertEqual(msg.as_server_request, MESSAGE_REQUEST["all"])
