"""Test for remote_services."""
import datetime
import re
from unittest import mock, TestCase


import requests_mock
from requests.exceptions import HTTPError

from bimmer_connected import remote_services
from bimmer_connected.remote_services import ExecutionState, RemoteServiceStatus

from . import RESPONSE_DIR, VIN_F45, load_response
from .test_account import get_mocked_account


_RESPONSE_INITIATED = RESPONSE_DIR / "remote_services" / "eadrax_service_initiated.json"
_RESPONSE_PENDING = RESPONSE_DIR / "remote_services" / "eadrax_service_pending.json"
_RESPONSE_DELIVERED = RESPONSE_DIR / "remote_services" / "eadrax_service_delivered.json"
_RESPONSE_EXECUTED = RESPONSE_DIR / "remote_services" / "eadrax_service_executed.json"


POI_DATA = {
    "lat": 37.4028943,
    "lon": -121.9700289,
    "name": "49ers",
    "additional_info": "Hi Sam",
    "street": "4949 Marie P DeBartolo Way",
    "city": "Santa Clara",
    "postal_code": "CA 95054",
    "country": "United States",
    "website": "https://www.49ers.com/",
    "phone_numbers": ["+1 408-562-4949"],
}


def get_remote_services_adapter():
    """Returns mocked adapter for auth."""
    adapter = requests_mock.Adapter()
    adapter.register_uri(
        "POST",
        re.compile(r"/eadrax-vrccs/v2/presentation/remote-commands/.+/.+$"),
        json=load_response(_RESPONSE_INITIATED),
    )
    adapter.register_uri(
        "POST",
        re.compile(r"/eadrax-vrccs/v2/presentation/remote-commands/eventStatus\?eventId=.+$"),
        [
            {"json": load_response(_RESPONSE_PENDING)},
            {"json": load_response(_RESPONSE_DELIVERED)},
            {"json": load_response(_RESPONSE_EXECUTED)},
        ],
    )
    adapter.register_uri("POST", "/eadrax-dcs/v1/send-to-car/send-to-car", status_code=201)
    return adapter


class TestRemoteServices(TestCase):
    """Test for remote_services."""

    # pylint: disable=protected-access

    def test_parse_timestamp(self):
        """Test parsing the timestamp format."""
        timestamp = RemoteServiceStatus._parse_timestamp("2018-02-11T15:10:39.465+01")
        expected = datetime.datetime(year=2018, month=2, day=11, hour=15, minute=10, second=39, microsecond=465000)
        self.assertEqual(expected, timestamp)

    def test_states(self):
        """Test parsing the different response types."""
        rss = RemoteServiceStatus(load_response(_RESPONSE_PENDING))
        self.assertEqual(ExecutionState.PENDING, rss.state)

        rss = RemoteServiceStatus(load_response(_RESPONSE_DELIVERED))
        self.assertEqual(ExecutionState.DELIVERED, rss.state)

        rss = RemoteServiceStatus(load_response(_RESPONSE_EXECUTED))
        self.assertEqual(ExecutionState.EXECUTED, rss.state)

    def test_trigger_remote_services(self):
        """Test executing a remote light flash."""
        remote_services._POLLING_CYCLE = 0
        remote_services._UPDATE_AFTER_REMOTE_SERVICE_DELAY = 0

        services = [
            ("LIGHT_FLASH", "trigger_remote_light_flash", False),
            ("DOOR_LOCK", "trigger_remote_door_lock", True),
            ("DOOR_UNLOCK", "trigger_remote_door_unlock", True),
            ("CLIMATE_NOW", "trigger_remote_air_conditioning", True),
            ("CLIMATE_STOP", "trigger_remote_air_conditioning_stop", True),
            ("VEHICLE_FINDER", "trigger_remote_vehicle_finder", True),
            ("HORN_BLOW", "trigger_remote_horn", False),
            ("SEND_POI", "trigger_send_poi", False),
        ]

        with requests_mock.Mocker(adapter=get_remote_services_adapter()):
            for service, call, triggers_update in services:
                account = get_mocked_account()
                mock_listener = mock.Mock(return_value=None)
                account.add_update_listener(mock_listener)
                vehicle = account.get_vehicle(VIN_F45)

                if service == "SEND_POI":
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
        account = get_mocked_account()
        vehicle = account.get_vehicle(VIN_F45)

        with requests_mock.Mocker() as mocker:
            mocker.post(
                "/eadrax-vrccs/v2/presentation/remote-commands/eventStatus?eventId=None",
                [
                    dict(status_code=500, json=[]),
                    dict(status_code=200, text="You can't parse this..."),
                ],
            )

            with self.assertRaises(HTTPError):
                vehicle.remote_services._get_remote_service_status(remote_services._Services.REMOTE_LIGHT_FLASH)
            with self.assertRaises(ValueError):
                vehicle.remote_services._get_remote_service_status(remote_services._Services.REMOTE_LIGHT_FLASH)

    def test_poi(self):
        """Test get_remove_service_status method."""
        account = get_mocked_account()
        vehicle = account.get_vehicle(VIN_F45)

        with requests_mock.Mocker(adapter=get_remote_services_adapter()):
            with self.assertRaises(TypeError):
                vehicle.remote_services.trigger_send_poi({"lat": 12.34})

    # TODO: POIs should be parsed correctly via a separate class

    # def test_parsing_of_poi_min_attributes(self):
    #     """Check that a PointOfInterest can be constructed using only latitude & longitude."""
    #     poi = PointOfInterest(POI_DATA["lat"], POI_DATA["lon"])
    #     msg = Message.from_poi(poi)
    #     self.assertEqual(msg.as_server_request, POI_REQUEST["min"])

    # def test_parsing_of_poi_all_attributes(self):
    #     """Check that a PointOfInterest can be constructed using all attributes."""
    #     poi = PointOfInterest(
    #         POI_DATA["lat"],
    #         POI_DATA["lon"],
    #         name=POI_DATA["name"],
    #         additional_info=POI_DATA["additional_info"],
    #         street=POI_DATA["street"],
    #         city=POI_DATA["city"],
    #         postal_code=POI_DATA["postal_code"],
    #         country=POI_DATA["country"],
    #         website=POI_DATA["website"],
    #         phone_numbers=POI_DATA["phone_numbers"],
    #     )
    #     msg = Message.from_poi(poi)
    #     self.assertEqual(msg.as_server_request, POI_REQUEST["all"])

    # def test_parsing_of_message_min_attributes(self):
    #     """Check that a Message can be constructed using text."""
    #     msg = Message.from_text(MESSAGE_DATA["text"])
    #     self.assertEqual(msg.as_server_request, MESSAGE_REQUEST["min"])

    # def test_parsing_of_message_all_attributes(self):
    #     """Check that a Message can be constructed using text."""
    #     msg = Message.from_text(MESSAGE_DATA["text"], MESSAGE_DATA["subject"])
    #     self.assertEqual(msg.as_server_request, MESSAGE_REQUEST["all"])
