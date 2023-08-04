"""Test for remote_services."""
import json
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Dict, List

from bimmer_connected.api.client import MyBMWClient
from bimmer_connected.models import MyBMWAPIError, MyBMWRemoteServiceError
from bimmer_connected.vehicle.charging_profile import ChargingMode

try:
    from unittest import mock

    if not hasattr(mock, "AsyncMock"):
        # AsyncMock was only introduced with Python3.8, so we have to use the backported module
        raise ImportError()
except ImportError:
    import mock  # type: ignore[import,no-redef]  # noqa: UP026

from uuid import uuid4

import httpx
import pytest
import time_machine

from bimmer_connected.models import ChargingSettings, PointOfInterest
from bimmer_connected.vehicle import remote_services
from bimmer_connected.vehicle.remote_services import ExecutionState, RemoteServiceStatus

from . import RESPONSE_DIR, VIN_F31, VIN_G01, VIN_G26, VIN_I01_NOREX, VIN_I20, load_response
from .test_account import account_mock, get_mocked_account

_RESPONSE_INITIATED = RESPONSE_DIR / "remote_services" / "eadrax_service_initiated.json"
_RESPONSE_PENDING = RESPONSE_DIR / "remote_services" / "eadrax_service_pending.json"
_RESPONSE_DELIVERED = RESPONSE_DIR / "remote_services" / "eadrax_service_delivered.json"
_RESPONSE_EXECUTED = RESPONSE_DIR / "remote_services" / "eadrax_service_executed.json"
_RESPONSE_ERROR = RESPONSE_DIR / "remote_services" / "eadrax_service_error.json"
_RESPONSE_EVENTPOSITION = RESPONSE_DIR / "remote_services" / "eadrax_service_eventposition.json"

remote_services._POLLING_CYCLE = 0

POI_DATA = {
    "lat": 37.4028943,
    "lon": -121.9700289,
    "name": "49ers",
    "street": "4949 Marie P DeBartolo Way",
    "city": "Santa Clara",
    "postal_code": "CA 95054",
    "country": "United States",
}

CHARGING_SETTINGS = {"target_soc": 75, "ac_limit": 16}

STATUS_RESPONSE_ORDER = [_RESPONSE_PENDING, _RESPONSE_DELIVERED, _RESPONSE_EXECUTED]
STATUS_RESPONSE_DICT: Dict[str, List[Path]] = defaultdict(lambda: deepcopy(STATUS_RESPONSE_ORDER))


def service_trigger_sideeffect(request: httpx.Request) -> httpx.Response:
    """Return specific eventId for each remote function."""
    json_data = load_response(_RESPONSE_INITIATED)
    json_data["eventId"] = str(uuid4())
    return httpx.Response(200, json=json_data)


def charging_settings_sideeffect(request: httpx.Request) -> httpx.Response:
    """Check if payload is a valid charging settings payload and return evendId."""
    _ = ChargingSettings(**json.loads(request.content))
    return service_trigger_sideeffect(request)


def charging_profile_sideeffect(request: httpx.Request) -> httpx.Response:
    """Check if payload is a valid charging settings payload and return evendId."""

    data = json.loads(request.content)

    if {"chargingMode", "departureTimer", "isPreconditionForDepartureActive", "servicePack"} != set(data):
        return httpx.Response(500)
    if (
        data["chargingMode"]["chargingPreference"] == "NO_PRESELECTION"
        and data["chargingMode"]["type"] != "CHARGING_IMMEDIATELY"
    ):
        return httpx.Response(500)
    if data["chargingMode"]["chargingPreference"] == "CHARGING_WINDOW" and data["chargingMode"]["type"] != "TIME_SLOT":
        return httpx.Response(500)

    if not isinstance(data["isPreconditionForDepartureActive"], bool):
        return httpx.Response(500)

    return service_trigger_sideeffect(request)


def service_status_sideeffect(request: httpx.Request) -> httpx.Response:
    """Return all 3 eventStatus responses per function."""
    response_data = STATUS_RESPONSE_DICT[request.url.params["eventId"]].pop(0)
    return httpx.Response(200, json=load_response(response_data))


def poi_sideeffect(request: httpx.Request) -> httpx.Response:
    """Check if payload is a valid POI."""
    data = json.loads(request.content)
    tests = all(
        [
            len(data["vin"]) == 17,
            isinstance(data["location"]["coordinates"]["latitude"], float),
            isinstance(data["location"]["coordinates"]["longitude"], float),
            len(data["location"]["name"]) > 0,
        ]
    )
    if not tests:
        return httpx.Response(400)
    return httpx.Response(201)


def remote_services_mock():
    """Return mocked adapter for auth."""
    router = account_mock()

    router.post(path__regex=r"/eadrax-vrccs/v3/presentation/remote-commands/.+/.+$").mock(
        side_effect=service_trigger_sideeffect
    )
    router.post(path__regex=r"/eadrax-crccs/v1/vehicles/.+/(start|stop)-charging$").mock(
        side_effect=service_trigger_sideeffect
    )
    router.post(path__regex=r"/eadrax-crccs/v1/vehicles/.+/charging-settings$").mock(
        side_effect=charging_settings_sideeffect
    )
    router.post(path__regex=r"/eadrax-crccs/v1/vehicles/.+/charging-profile$").mock(
        side_effect=charging_profile_sideeffect
    )
    router.post("/eadrax-vrccs/v3/presentation/remote-commands/eventStatus", params={"eventId": mock.ANY}).mock(
        side_effect=service_status_sideeffect
    )

    router.post("/eadrax-dcs/v1/send-to-car/send-to-car").mock(side_effect=poi_sideeffect)
    router.post("/eadrax-vrccs/v3/presentation/remote-commands/eventPosition", params={"eventId": mock.ANY}).respond(
        200,
        json=load_response(_RESPONSE_EVENTPOSITION),
    )
    return router


def test_states():
    """Test parsing the different response types."""
    rss = RemoteServiceStatus(load_response(_RESPONSE_PENDING))
    assert ExecutionState.PENDING == rss.state

    rss = RemoteServiceStatus(load_response(_RESPONSE_DELIVERED))
    assert ExecutionState.DELIVERED == rss.state

    rss = RemoteServiceStatus(load_response(_RESPONSE_EXECUTED))
    assert ExecutionState.EXECUTED == rss.state


ALL_SERVICES = {
    "LIGHT_FLASH": {"call": "trigger_remote_light_flash", "refresh": False},
    "DOOR_LOCK": {"call": "trigger_remote_door_lock", "refresh": True},
    "DOOR_UNLOCK": {"call": "trigger_remote_door_unlock", "refresh": True},
    "CLIMATE_NOW": {"call": "trigger_remote_air_conditioning", "refresh": True},
    "CLIMATE_STOP": {"call": "trigger_remote_air_conditioning_stop", "refresh": True},
    "VEHICLE_FINDER": {"call": "trigger_remote_vehicle_finder", "refresh": False},
    "HORN_BLOW": {"call": "trigger_remote_horn", "refresh": False},
    "SEND_POI": {"call": "trigger_send_poi", "refresh": False, "args": [POI_DATA]},
    "CHARGE_START": {"call": "trigger_charge_start", "refresh": True},
    "CHARGE_STOP": {"call": "trigger_charge_stop", "refresh": True},
    "CHARGING_SETTINGS": {"call": "trigger_charging_settings_update", "refresh": True, "kwargs": CHARGING_SETTINGS},
}


@remote_services_mock()
@pytest.mark.asyncio
@pytest.mark.filterwarnings("ignore:coroutine 'AsyncMockMixin._execute_mock_call' was never awaited:RuntimeWarning")
async def test_trigger_remote_services():
    """Test executing a remote light flash."""

    account = await get_mocked_account()
    vehicle = account.get_vehicle(VIN_I20)

    for service in ALL_SERVICES.values():
        with mock.patch(
            "bimmer_connected.account.MyBMWAccount.get_vehicles", new_callable=mock.AsyncMock
        ) as mock_listener:
            mock_listener.reset_mock()

            response = await getattr(vehicle.remote_services, service["call"])(
                *service.get("args", []), **service.get("kwargs", {})
            )
            assert ExecutionState.EXECUTED == response.state

            if service["refresh"]:
                mock_listener.assert_called_once_with()
            else:
                mock_listener.assert_not_called()


@pytest.mark.asyncio
async def test_get_remote_service_status():
    """Test get_remove_service_status method."""

    account = await get_mocked_account()
    vehicle = account.get_vehicle(VIN_G26)
    client = MyBMWClient(account.config)

    with remote_services_mock() as mock_api:
        mock_api.post("/eadrax-vrccs/v3/presentation/remote-commands/eventStatus", params={"eventId": mock.ANY}).mock(
            side_effect=[
                httpx.Response(500),
                httpx.Response(200, text="You can't parse this..."),
                httpx.Response(200, json=load_response(_RESPONSE_ERROR)),
            ],
        )

        with pytest.raises(MyBMWAPIError):
            await vehicle.remote_services._block_until_done(client, uuid4())
        with pytest.raises(ValueError):
            await vehicle.remote_services._block_until_done(client, uuid4())
        with pytest.raises(MyBMWRemoteServiceError):
            await vehicle.remote_services._block_until_done(client, uuid4())


@remote_services_mock()
@pytest.mark.asyncio
async def test_set_charging_settings():
    """Test setting the charging settings on a car."""

    account = await get_mocked_account()

    # Errors on old electric vehicles, combustion engines and PHEV
    for vin in [VIN_I01_NOREX, VIN_F31, VIN_G01]:
        vehicle = account.get_vehicle(vin)
        with pytest.raises(ValueError):
            await vehicle.remote_services.trigger_charging_settings_update(target_soc=80)
        with pytest.raises(ValueError):
            await vehicle.remote_services.trigger_charging_settings_update(ac_limit=16)

    # This shouldn't fail
    vehicle = account.get_vehicle(VIN_G26)
    await vehicle.remote_services.trigger_charging_settings_update(target_soc=80, ac_limit=16)

    # But these are not allowed
    with pytest.raises(ValueError):
        await vehicle.remote_services.trigger_charging_settings_update(target_soc=19)
    with pytest.raises(ValueError):
        await vehicle.remote_services.trigger_charging_settings_update(target_soc=21)
    with pytest.raises(ValueError):
        await vehicle.remote_services.trigger_charging_settings_update(target_soc=101)
    with pytest.raises(ValueError):
        await vehicle.remote_services.trigger_charging_settings_update(target_soc="asdf")
    with pytest.raises(ValueError):
        await vehicle.remote_services.trigger_charging_settings_update(ac_limit=17)
    with pytest.raises(ValueError):
        await vehicle.remote_services.trigger_charging_settings_update(ac_limit="asdf")


@remote_services_mock()
@pytest.mark.asyncio
async def test_set_charging_profile():
    """Test setting the charging profile on a car."""

    account = await get_mocked_account()

    # Errors on combustion engines
    vehicle = account.get_vehicle(VIN_F31)
    with pytest.raises(ValueError):
        await vehicle.remote_services.trigger_charging_profile_update(precondition_climate=True)

    # This shouldn't fail even on older EV
    vehicle = account.get_vehicle(VIN_I01_NOREX)
    await vehicle.remote_services.trigger_charging_profile_update(
        charging_mode=ChargingMode.IMMEDIATE_CHARGING, precondition_climate=True
    )

    await vehicle.remote_services.trigger_charging_profile_update(charging_mode=ChargingMode.IMMEDIATE_CHARGING)
    await vehicle.remote_services.trigger_charging_profile_update(precondition_climate=True)


@remote_services_mock()
@pytest.mark.asyncio
async def test_vehicles_without_enabled_services():
    """Test setting the charging profile on a car."""

    account = await get_mocked_account()

    # Errors on combustion engines
    vehicle = account.get_vehicle(VIN_F31)

    vehicle.update_state(vehicle.data, {"capabilities": {}})

    for service in ALL_SERVICES.values():
        with pytest.raises(ValueError):
            await getattr(vehicle.remote_services, service["call"])(
                *service.get("args", []), **service.get("kwargs", {})
            )


@remote_services_mock()
@pytest.mark.asyncio
async def test_trigger_charge_start_stop_warnings(caplog):
    """Test if warnings are produced correctly with the charge start/stop services."""

    account = await get_mocked_account()
    vehicle = account.get_vehicle(VIN_I20)

    fixture_not_connected = {
        **vehicle.data["state"]["electricChargingState"],
        "chargingStatus": "INVALID",
        "isChargerConnected": False,
    }
    vehicle.update_state(vehicle.data, {"state": {"electricChargingState": fixture_not_connected}})

    result = await vehicle.remote_services.trigger_charge_start()
    assert result.state == ExecutionState.IGNORED
    assert len([r for r in caplog.records if r.levelname == "WARNING" and "Charger not connected" in r.message]) == 1
    caplog.clear()

    result = await vehicle.remote_services.trigger_charge_stop()
    assert result.state == ExecutionState.IGNORED
    assert len([r for r in caplog.records if r.levelname == "WARNING" and "Charger not connected" in r.message]) == 1
    caplog.clear()

    fixture_connected_not_charging = {
        **vehicle.data["state"]["electricChargingState"],
        "chargingStatus": "WAITING_FOR_CHARGING",
        "isChargerConnected": True,
    }
    vehicle.update_state(vehicle.data, {"state": {"electricChargingState": fixture_connected_not_charging}})

    result = await vehicle.remote_services.trigger_charge_stop()
    assert result.state == ExecutionState.IGNORED
    assert len([r for r in caplog.records if r.levelname == "WARNING" and "Vehicle not charging" in r.message]) == 1
    caplog.clear()


@remote_services_mock()
@pytest.mark.asyncio
async def test_get_remote_position():
    """Test getting position from remote service."""

    account = await get_mocked_account()
    account.set_observer_position(1.0, 0.0)
    vehicle = account.get_vehicle(VIN_G26)
    status = vehicle.status

    # Check original position
    assert (48.177334, 11.556274) == status.gps_position
    assert 180 == status.gps_heading

    # Check updated position
    await vehicle.remote_services.trigger_remote_vehicle_finder()
    assert (123.456, 34.5678) == status.gps_position
    assert 121 == status.gps_heading

    # Position should still be from vehicle finder after status update
    await account.get_vehicles()
    assert (123.456, 34.5678) == status.gps_position
    assert 121 == status.gps_heading


@remote_services_mock()
@pytest.mark.asyncio
async def test_get_remote_position_fail_without_observer(caplog):
    """Test getting position from remote service."""

    account = await get_mocked_account()
    vehicle = account.get_vehicle(VIN_G26)

    await vehicle.remote_services.trigger_remote_vehicle_finder()
    errors = [
        r
        for r in caplog.records
        if r.levelname == "ERROR"
        and "Unknown position: Set observer position to retrieve vehicle coordinates" in r.message
    ]
    assert len(errors) == 1


@remote_services_mock()
@pytest.mark.asyncio
async def test_fail_with_timeout():
    """Test failing after timeout was reached."""
    remote_services._POLLING_CYCLE = 1
    remote_services._POLLING_TIMEOUT = 2

    account = await get_mocked_account()
    vehicle = account.get_vehicle(VIN_G26)

    with pytest.raises(MyBMWRemoteServiceError):
        await vehicle.remote_services.trigger_remote_light_flash()


@time_machine.travel("2020-01-01", tick=False)
@remote_services_mock()
@pytest.mark.asyncio
async def test_get_remote_position_too_old():
    """Test remote service position being ignored as vehicle status is newer."""

    account = await get_mocked_account()
    vehicle = account.get_vehicle(VIN_G26)
    status = vehicle.status

    await vehicle.remote_services.trigger_remote_vehicle_finder()

    assert (48.177334, 11.556274) == status.gps_position
    assert 180 == status.gps_heading


@remote_services_mock()
@pytest.mark.asyncio
async def test_poi():
    """Test get_remove_service_status method."""

    account = await get_mocked_account()
    vehicle = account.get_vehicle(VIN_G26)

    await vehicle.remote_services.trigger_send_poi({"lat": 12.34, "lon": 12.34})

    with pytest.raises(TypeError):
        await vehicle.remote_services.trigger_send_poi({"lat": 12.34})


def test_poi_parsing():
    """Test correct parsing of PointOfInterest."""

    poi_data = PointOfInterest(**POI_DATA)

    # Check parsing of attributes required by API
    assert poi_data.coordinates.latitude == POI_DATA["lat"]
    assert poi_data.coordinates.longitude == POI_DATA["lon"]
    assert poi_data.name == POI_DATA["name"]
    assert poi_data.formattedAddress == f"{POI_DATA['street']}, {POI_DATA['postal_code']}, {POI_DATA['city']}"

    # Check the default attributes
    poi_data = PointOfInterest(lat=POI_DATA["lat"], lon=POI_DATA["lon"])
    assert poi_data.coordinates.latitude == POI_DATA["lat"]
    assert poi_data.coordinates.longitude == POI_DATA["lon"]
    assert poi_data.name == "Sent with ♥ by bimmer_connected"
    assert poi_data.formattedAddress == "Coordinates only"

    # Check the default attributes with formatted address
    poi_data = PointOfInterest(lat=POI_DATA["lat"], lon=POI_DATA["lon"], formattedAddress="Somewhere over rainbow")
    assert poi_data.coordinates.latitude == POI_DATA["lat"]
    assert poi_data.coordinates.longitude == POI_DATA["lon"]
    assert poi_data.name == "Sent with ♥ by bimmer_connected"
    assert poi_data.formattedAddress == "Somewhere over rainbow"
