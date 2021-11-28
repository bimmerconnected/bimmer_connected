"""Test for remote_services."""
import datetime
import logging
import re

from unittest import TestCase, mock

import time_machine
import requests_mock
from requests.exceptions import HTTPError

from bimmer_connected import remote_services
from bimmer_connected.remote_services import ExecutionState, RemoteServiceStatus


from . import RESPONSE_DIR, VIN_F45, load_response
from .test_account import get_base_adapter, get_mocked_account

_RESPONSE_INITIATED = RESPONSE_DIR / "remote_services" / "eadrax_service_initiated.json"
_RESPONSE_PENDING = RESPONSE_DIR / "remote_services" / "eadrax_service_pending.json"
_RESPONSE_DELIVERED = RESPONSE_DIR / "remote_services" / "eadrax_service_delivered.json"
_RESPONSE_EXECUTED = RESPONSE_DIR / "remote_services" / "eadrax_service_executed.json"
_RESPONSE_EVENTPOSITION = RESPONSE_DIR / "remote_services" / "eadrax_service_eventposition.json"


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
    adapter = get_base_adapter()
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
    adapter.register_uri(
        "POST",
        re.compile(r"/eadrax-vrccs/v2/presentation/remote-commands/eventPosition\?eventId=.+$"),
        json=load_response(_RESPONSE_EVENTPOSITION),
    )
    return adapter


class TestRemoteServices(TestCase):
    """Test for remote_services."""

    # pylint: disable=protected-access

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
            ("VEHICLE_FINDER", "trigger_remote_vehicle_finder", False),
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
        remote_services._POLLING_CYCLE = 0
        remote_services._UPDATE_AFTER_REMOTE_SERVICE_DELAY = 0

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

    def test_get_remote_position(self):
        """Test getting position from remote service."""
        remote_services._POLLING_CYCLE = 0
        remote_services._UPDATE_AFTER_REMOTE_SERVICE_DELAY = 0

        with requests_mock.Mocker(adapter=get_remote_services_adapter()):
            account = get_mocked_account()
            account.set_observer_position(1.0, 0.0)
            vehicle = account.get_vehicle(VIN_F45)
            status = vehicle.status

            # Check original position
            self.assertTupleEqual((12.3456, 34.5678), status.gps_position)
            self.assertAlmostEqual(123, status.gps_heading)

            # Check updated position
            vehicle.remote_services.trigger_remote_vehicle_finder()
            self.assertTupleEqual((123.456, 34.5678), status.gps_position)
            self.assertAlmostEqual(121, status.gps_heading)

            # Position should still be from vehicle finder after status update
            account._get_vehicles()
            self.assertTupleEqual((123.456, 34.5678), status.gps_position)
            self.assertAlmostEqual(121, status.gps_heading)

    def test_get_remote_position_fail_without_observer(self):
        """Test getting position from remote service."""
        remote_services._POLLING_CYCLE = 0
        remote_services._UPDATE_AFTER_REMOTE_SERVICE_DELAY = 0

        with requests_mock.Mocker(adapter=get_remote_services_adapter()):
            account = get_mocked_account()
            vehicle = account.get_vehicle(VIN_F45)

            with self.assertLogs(level=logging.ERROR):
                vehicle.remote_services.trigger_remote_vehicle_finder()

    @time_machine.travel(datetime.date(2020, 1, 1))
    def test_get_remote_position_too_old(self):
        """Test remote service position being ignored as vehicle status is newer."""
        remote_services._POLLING_CYCLE = 0
        remote_services._UPDATE_AFTER_REMOTE_SERVICE_DELAY = 0

        with requests_mock.Mocker(adapter=get_remote_services_adapter()):
            account = get_mocked_account()
            vehicle = account.get_vehicle(VIN_F45)
            status = vehicle.status

            vehicle.remote_services.trigger_remote_vehicle_finder()

            self.assertTupleEqual((12.3456, 34.5678), status.gps_position)
            self.assertAlmostEqual(123, status.gps_heading)

    def test_poi(self):
        """Test get_remove_service_status method."""
        remote_services._POLLING_CYCLE = 0
        remote_services._UPDATE_AFTER_REMOTE_SERVICE_DELAY = 0

        account = get_mocked_account()
        vehicle = account.get_vehicle(VIN_F45)

        with requests_mock.Mocker(adapter=get_remote_services_adapter()):
            with self.assertRaises(TypeError):
                vehicle.remote_services.trigger_send_poi({"lat": 12.34})
