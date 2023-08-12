"""Test for remote_services."""
from unittest import mock
from uuid import uuid4

import httpx
import pytest
import respx
import time_machine

from bimmer_connected.api.client import MyBMWClient
from bimmer_connected.models import MyBMWAPIError, MyBMWRemoteServiceError, PointOfInterest
from bimmer_connected.vehicle import remote_services
from bimmer_connected.vehicle.charging_profile import ChargingMode
from bimmer_connected.vehicle.climate import ClimateActivityState
from bimmer_connected.vehicle.doors_windows import LockState
from bimmer_connected.vehicle.fuel_and_battery import ChargingState
from bimmer_connected.vehicle.remote_services import ExecutionState, RemoteServiceStatus

from . import (
    REMOTE_SERVICE_RESPONSE_DELIVERED,
    REMOTE_SERVICE_RESPONSE_ERROR,
    REMOTE_SERVICE_RESPONSE_EXECUTED,
    REMOTE_SERVICE_RESPONSE_PENDING,
    VIN_F31,
    VIN_G01,
    VIN_G26,
    VIN_I01_NOREX,
    VIN_I20,
    load_response,
)
from .common import (
    CHARGING_SETTINGS,
    POI_DATA,
)
from .conftest import prepare_account_with_vehicles

remote_services._POLLING_CYCLE = 0


def test_states():
    """Test parsing the different response types."""
    rss = RemoteServiceStatus(load_response(REMOTE_SERVICE_RESPONSE_PENDING))
    assert ExecutionState.PENDING == rss.state

    rss = RemoteServiceStatus(load_response(REMOTE_SERVICE_RESPONSE_DELIVERED))
    assert ExecutionState.DELIVERED == rss.state

    rss = RemoteServiceStatus(load_response(REMOTE_SERVICE_RESPONSE_EXECUTED))
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


@pytest.mark.asyncio
@pytest.mark.filterwarnings("ignore:coroutine 'AsyncMockMixin._execute_mock_call' was never awaited:RuntimeWarning")
async def test_trigger_remote_services(bmw_fixture: respx.Router):
    """Test executing a remote light flash."""

    account = await prepare_account_with_vehicles()
    vehicle = account.get_vehicle(VIN_I20)

    for service in ALL_SERVICES.values():
        with mock.patch(
            "bimmer_connected.account.MyBMWAccount.get_vehicles", new_callable=mock.AsyncMock
        ) as mock_listener:
            mock_listener.reset_mock()

            response = await getattr(vehicle.remote_services, service["call"])(  # type: ignore[call-overload]
                *service.get("args", []), **service.get("kwargs", {})
            )
            assert ExecutionState.EXECUTED == response.state

            if service["refresh"]:
                mock_listener.assert_called_once_with()
            else:
                mock_listener.assert_not_called()


@pytest.mark.asyncio
async def test_get_remote_service_status(bmw_fixture: respx.Router):
    """Test get_remove_service_status method."""

    account = await prepare_account_with_vehicles()
    vehicle = account.get_vehicle(VIN_G26)
    client = MyBMWClient(account.config)

    bmw_fixture.post("/eadrax-vrccs/v3/presentation/remote-commands/eventStatus", params={"eventId": mock.ANY}).mock(
        side_effect=[
            httpx.Response(500),
            httpx.Response(200, text="You can't parse this..."),
            httpx.Response(200, json=load_response(REMOTE_SERVICE_RESPONSE_ERROR)),
        ],
    )

    with pytest.raises(MyBMWAPIError):
        await vehicle.remote_services._block_until_done(client, uuid4())
    with pytest.raises(ValueError):
        await vehicle.remote_services._block_until_done(client, uuid4())
    with pytest.raises(MyBMWRemoteServiceError):
        await vehicle.remote_services._block_until_done(client, uuid4())


@pytest.mark.asyncio
async def test_set_lock_result(bmw_fixture: respx.Router):
    """Test locking/unlocking a car."""

    account = await prepare_account_with_vehicles()

    vehicle = account.get_vehicle(VIN_I01_NOREX)
    # check current state, unlock vehicle, check changed state
    assert vehicle.doors_and_windows.door_lock_state == LockState.UNLOCKED
    await vehicle.remote_services.trigger_remote_door_lock()
    assert vehicle.doors_and_windows.door_lock_state == LockState.LOCKED

    # now lock vehicle again, check changed state
    await vehicle.remote_services.trigger_remote_door_unlock()
    assert vehicle.doors_and_windows.door_lock_state == LockState.UNLOCKED


@pytest.mark.asyncio
async def test_set_climate_result(bmw_fixture: respx.Router):
    """Test starting/stopping climatization."""

    account = await prepare_account_with_vehicles()

    vehicle = account.get_vehicle(VIN_G01)
    # check current state, unlock vehicle, check changed state
    assert vehicle.climate.activity == ClimateActivityState.STANDBY
    await vehicle.remote_services.trigger_remote_air_conditioning()
    assert vehicle.climate.activity in [ClimateActivityState.COOLING, ClimateActivityState.HEATING]

    # now lock vehicle again, check changed state
    await vehicle.remote_services.trigger_remote_air_conditioning_stop()
    assert vehicle.climate.activity == ClimateActivityState.STANDBY


@pytest.mark.asyncio
async def test_charging_start_stop(bmw_fixture: respx.Router):
    """Test starting/stopping climatization."""

    account = await prepare_account_with_vehicles()

    vehicle = account.get_vehicle(VIN_I20)

    # check current state, unlock vehicle, check changed state
    assert vehicle.fuel_and_battery.charging_status == ChargingState.CHARGING
    await vehicle.remote_services.trigger_charge_stop()
    assert vehicle.fuel_and_battery.charging_status == ChargingState.PLUGGED_IN

    # now lock vehicle again, check changed state
    await vehicle.remote_services.trigger_charge_start()
    assert vehicle.fuel_and_battery.charging_status == ChargingState.CHARGING


@pytest.mark.asyncio
async def test_set_charging_settings(bmw_fixture: respx.Router):
    """Test setting the charging settings on a car."""

    account = await prepare_account_with_vehicles()

    # Errors on old electric vehicles, combustion engines and PHEV
    for vin in [VIN_I01_NOREX, VIN_F31, VIN_G01]:
        vehicle = account.get_vehicle(vin)
        with pytest.raises(ValueError):
            await vehicle.remote_services.trigger_charging_settings_update(target_soc=80)
        with pytest.raises(ValueError):
            await vehicle.remote_services.trigger_charging_settings_update(ac_limit=16)

    # This should work
    vehicle = account.get_vehicle(VIN_G26)
    # Test current state
    assert vehicle.charging_profile.ac_current_limit == 16
    assert vehicle.fuel_and_battery.charging_target == 80
    # Update settings
    await vehicle.remote_services.trigger_charging_settings_update(target_soc=75, ac_limit=12)
    # Test changed state
    assert vehicle.charging_profile.ac_current_limit == 12
    assert vehicle.fuel_and_battery.charging_target == 75

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


@pytest.mark.asyncio
async def test_set_charging_profile(bmw_fixture: respx.Router):
    """Test setting the charging profile on a car."""

    account = await prepare_account_with_vehicles()

    # Errors on combustion engines
    vehicle = account.get_vehicle(VIN_F31)
    with pytest.raises(ValueError):
        await vehicle.remote_services.trigger_charging_profile_update(precondition_climate=True)

    # This shouldn't fail even on older EV
    vehicle = account.get_vehicle(VIN_I01_NOREX)
    # check current state
    assert vehicle.charging_profile.charging_mode == ChargingMode.IMMEDIATE_CHARGING
    assert vehicle.charging_profile.is_pre_entry_climatization_enabled is True

    # update two settings
    await vehicle.remote_services.trigger_charging_profile_update(
        charging_mode=ChargingMode.DELAYED_CHARGING, precondition_climate=False
    )
    assert vehicle.charging_profile.charging_mode == ChargingMode.DELAYED_CHARGING
    assert vehicle.charging_profile.is_pre_entry_climatization_enabled is False

    # change back only charging mode
    await vehicle.remote_services.trigger_charging_profile_update(charging_mode=ChargingMode.IMMEDIATE_CHARGING)
    assert vehicle.charging_profile.charging_mode == ChargingMode.IMMEDIATE_CHARGING

    # change back only climatization
    await vehicle.remote_services.trigger_charging_profile_update(precondition_climate=True)
    assert vehicle.charging_profile.is_pre_entry_climatization_enabled is True


@pytest.mark.asyncio
async def test_vehicles_without_enabled_services(bmw_fixture: respx.Router):
    """Test setting the charging profile on a car."""

    account = await prepare_account_with_vehicles()

    # Errors on combustion engines
    vehicle = account.get_vehicle(VIN_F31)

    vehicle.update_state(vehicle.data, {"capabilities": {}})

    for service in ALL_SERVICES.values():
        with pytest.raises(ValueError):
            await getattr(vehicle.remote_services, service["call"])(  # type: ignore[call-overload]
                *service.get("args", []), **service.get("kwargs", {})
            )


@pytest.mark.asyncio
async def test_trigger_charge_start_stop_warnings(caplog, bmw_fixture: respx.Router):
    """Test if warnings are produced correctly with the charge start/stop services."""

    account = await prepare_account_with_vehicles()
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


@pytest.mark.asyncio
async def test_get_remote_position(bmw_fixture: respx.Router):
    """Test getting position from remote service."""

    account = await prepare_account_with_vehicles()
    account.set_observer_position(1.0, 0.0)
    vehicle = account.get_vehicle(VIN_G26)
    location = vehicle.vehicle_location

    # Check original position
    assert (48.177334, 11.556274) == location.location
    assert 180 == location.heading

    # Check updated position
    await vehicle.remote_services.trigger_remote_vehicle_finder()
    assert (123.456, 34.5678) == location.location
    assert 121 == location.heading

    # Position should still be from vehicle finder after status update
    await account.get_vehicles()
    assert (123.456, 34.5678) == location.location
    assert 121 == location.heading


@pytest.mark.asyncio
async def test_get_remote_position_fail_without_observer(caplog, bmw_fixture: respx.Router):
    """Test getting position from remote service."""

    account = await prepare_account_with_vehicles()
    vehicle = account.get_vehicle(VIN_G26)

    await vehicle.remote_services.trigger_remote_vehicle_finder()
    errors = [
        r
        for r in caplog.records
        if r.levelname == "ERROR"
        and "Unknown position: Set observer position to retrieve vehicle coordinates" in r.message
    ]
    assert len(errors) == 1


@pytest.mark.asyncio
async def test_fail_with_timeout(bmw_fixture: respx.Router):
    """Test failing after timeout was reached."""
    remote_services._POLLING_CYCLE = 1
    remote_services._POLLING_TIMEOUT = 2

    account = await prepare_account_with_vehicles()
    vehicle = account.get_vehicle(VIN_G26)

    with pytest.raises(MyBMWRemoteServiceError):
        await vehicle.remote_services.trigger_remote_light_flash()


@time_machine.travel("2020-01-01", tick=False)
@pytest.mark.asyncio
async def test_get_remote_position_too_old(bmw_fixture: respx.Router):
    """Test remote service position being ignored as vehicle status is newer."""

    account = await prepare_account_with_vehicles()
    vehicle = account.get_vehicle(VIN_G26)
    location = vehicle.vehicle_location

    await vehicle.remote_services.trigger_remote_vehicle_finder()

    assert (48.177334, 11.556274) == location.location
    assert 180 == location.heading


@pytest.mark.asyncio
async def test_poi(bmw_fixture: respx.Router):
    """Test get_remove_service_status method."""

    account = await prepare_account_with_vehicles()
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
