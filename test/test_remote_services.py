"""Test for remote_services."""
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Dict, List

try:
    from unittest import mock

    if not hasattr(mock, "AsyncMock"):
        # AsyncMock was only introduced with Python3.8, so we have to use the backported module
        raise ImportError()
except ImportError:
    import mock  # type: ignore[import,no-redef]

from uuid import uuid4

import httpx
import pytest
import time_machine

from bimmer_connected.vehicle import remote_services
from bimmer_connected.vehicle.remote_services import ExecutionState, RemoteServiceStatus

from . import RESPONSE_DIR, VIN_F45, load_response
from .test_account import account_mock, get_mocked_account

_RESPONSE_INITIATED = RESPONSE_DIR / "remote_services" / "eadrax_service_initiated.json"
_RESPONSE_PENDING = RESPONSE_DIR / "remote_services" / "eadrax_service_pending.json"
_RESPONSE_DELIVERED = RESPONSE_DIR / "remote_services" / "eadrax_service_delivered.json"
_RESPONSE_EXECUTED = RESPONSE_DIR / "remote_services" / "eadrax_service_executed.json"
_RESPONSE_ERROR = RESPONSE_DIR / "remote_services" / "eadrax_service_error.json"
_RESPONSE_EVENTPOSITION = RESPONSE_DIR / "remote_services" / "eadrax_service_eventposition.json"


POI_DATA = {
    "lat": 37.4028943,
    "lon": -121.9700289,
    "name": "49ers",
    "street": "4949 Marie P DeBartolo Way",
    "city": "Santa Clara",
    "postal_code": "CA 95054",
    "country": "United States",
}

STATUS_RESPONSE_ORDER = [_RESPONSE_PENDING, _RESPONSE_DELIVERED, _RESPONSE_EXECUTED]
STATUS_RESPONSE_DICT: Dict[str, List[Path]] = defaultdict(lambda: deepcopy(STATUS_RESPONSE_ORDER))


def service_trigger_sideeffect(request: httpx.Request) -> httpx.Response:  # pylint: disable=unused-argument
    """Returns specific eventId for each remote function."""
    json_data = load_response(_RESPONSE_INITIATED)
    json_data["eventId"] = str(uuid4())
    return httpx.Response(200, json=json_data)


def service_status_sideeffect(request: httpx.Request) -> httpx.Response:
    """Returns all 3 eventStatus responses per function."""
    response_data = STATUS_RESPONSE_DICT[request.url.params["eventId"]].pop(0)
    return httpx.Response(200, json=load_response(response_data))


def remote_services_mock():
    """Returns mocked adapter for auth."""
    router = account_mock()

    router.post(path__regex=r"/eadrax-vrccs/v2/presentation/remote-commands/.+/.+$").mock(
        side_effect=service_trigger_sideeffect
    )
    router.post("/eadrax-vrccs/v2/presentation/remote-commands/eventStatus", params={"eventId": mock.ANY}).mock(
        side_effect=service_status_sideeffect
    )

    router.post("/eadrax-dcs/v1/send-to-car/send-to-car").respond(201)
    router.post("/eadrax-vrccs/v2/presentation/remote-commands/eventPosition", params={"eventId": mock.ANY}).respond(
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


@remote_services_mock()
@pytest.mark.asyncio
@pytest.mark.filterwarnings("ignore:coroutine 'AsyncMockMixin._execute_mock_call' was never awaited:RuntimeWarning")
async def test_trigger_remote_services():
    """Test executing a remote light flash."""
    remote_services._POLLING_CYCLE = 0  # pylint: disable=protected-access

    services = [
        ("LIGHT_FLASH", "trigger_remote_light_flash", False),
        ("DOOR_LOCK", "trigger_remote_door_lock", True),
        ("DOOR_UNLOCK", "trigger_remote_door_unlock", True),
        ("CLIMATE_NOW", "trigger_remote_air_conditioning", True),
        ("CLIMATE_STOP", "trigger_remote_air_conditioning_stop", True),
        ("VEHICLE_FINDER", "trigger_remote_vehicle_finder", False),
        ("HORN_BLOW", "trigger_remote_horn", False),
        ("SEND_POI", "trigger_send_poi", False),
        ("CHARGE_NOW", "trigger_charge_now", True),
    ]

    account = await get_mocked_account()
    vehicle = account.get_vehicle(VIN_F45)

    for service, call, triggers_update in services:
        with mock.patch(
            "bimmer_connected.account.MyBMWAccount.get_vehicles", new_callable=mock.AsyncMock
        ) as mock_listener:
            mock_listener.reset_mock()

            if service == "SEND_POI":
                response = await getattr(vehicle.remote_services, call)(POI_DATA)
            else:
                response = await getattr(vehicle.remote_services, call)()
                assert ExecutionState.EXECUTED == response.state

                if triggers_update:
                    mock_listener.assert_called_once_with()
                else:
                    mock_listener.assert_not_called()


@pytest.mark.asyncio
async def test_get_remote_service_status():
    """Test get_remove_service_status method."""
    # pylint: disable=protected-access
    remote_services._POLLING_CYCLE = 0

    account = await get_mocked_account()
    vehicle = account.get_vehicle(VIN_F45)

    with remote_services_mock() as mock_api:
        mock_api.post("/eadrax-vrccs/v2/presentation/remote-commands/eventStatus", params={"eventId": mock.ANY}).mock(
            side_effect=[
                httpx.Response(500),
                httpx.Response(200, text="You can't parse this..."),
                httpx.Response(200, json=load_response(_RESPONSE_ERROR)),
            ],
        )

        with pytest.raises(httpx.HTTPStatusError):
            await vehicle.remote_services._block_until_done(uuid4())
        with pytest.raises(ValueError):
            await vehicle.remote_services._block_until_done(uuid4())
        with pytest.raises(Exception):
            await vehicle.remote_services._block_until_done(uuid4())


@remote_services_mock()
@pytest.mark.asyncio
async def test_get_remote_position():
    """Test getting position from remote service."""
    remote_services._POLLING_CYCLE = 0  # pylint: disable=protected-access

    account = await get_mocked_account()
    account.set_observer_position(1.0, 0.0)
    vehicle = account.get_vehicle(VIN_F45)
    status = vehicle.status

    # Check original position
    assert (12.3456, 34.5678) == status.gps_position
    assert 123 == status.gps_heading

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
    remote_services._POLLING_CYCLE = 0  # pylint: disable=protected-access

    account = await get_mocked_account()
    vehicle = account.get_vehicle(VIN_F45)

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
    remote_services._POLLING_CYCLE = 1  # pylint: disable=protected-access
    remote_services._POLLING_TIMEOUT = 2  # pylint: disable=protected-access

    account = await get_mocked_account()
    vehicle = account.get_vehicle(VIN_F45)

    with pytest.raises(TimeoutError):
        await vehicle.remote_services.trigger_remote_light_flash()


@time_machine.travel("2020-01-01", tick=False)
@remote_services_mock()
@pytest.mark.asyncio
async def test_get_remote_position_too_old():
    """Test remote service position being ignored as vehicle status is newer."""
    remote_services._POLLING_CYCLE = 0  # pylint: disable=protected-access

    account = await get_mocked_account()
    vehicle = account.get_vehicle(VIN_F45)
    status = vehicle.status

    await vehicle.remote_services.trigger_remote_vehicle_finder()

    assert (12.3456, 34.5678) == status.gps_position
    assert 123 == status.gps_heading


@remote_services_mock()
@pytest.mark.asyncio
async def test_poi():
    """Test get_remove_service_status method."""
    remote_services._POLLING_CYCLE = 0  # pylint: disable=protected-access

    account = await get_mocked_account()
    vehicle = account.get_vehicle(VIN_F45)

    with pytest.raises(TypeError):
        await vehicle.remote_services.trigger_send_poi({"lat": 12.34})
